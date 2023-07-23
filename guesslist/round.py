from flask import Blueprint, flash, g, redirect, render_template, request, url_for
import requests
import base64
import random
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db

bp = Blueprint("round", __name__, url_prefix="/round")

# TODO Store this stuff somewhere else
BASE_URL = "https://api.spotify.com/v1/"
SPOTIFY_USER_ID = "***REMOVED***"
CLIENT_ID = "***REMOVED***"
CLIENT_SECRET = "***REMOVED***"
REFRESH_TOKEN = "***REMOVED***"
CLIENT_ID_SECRET_B64 = (
    "Basic " + base64.b64encode((CLIENT_ID + ":" + CLIENT_SECRET).encode()).decode()
)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add():
    # For admin to add a round to club
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        error = None

        if not name:
            error = "Name is required."

        elif not name:
            error = "Description is required."

        if error is not None:
            flash(error)
        else:
            add_round(name, description, g.user["club_id"])
            return redirect(url_for("index.index"))

    return render_template("round/add.html")


def add_round(name, description, club_id):
    latest_round_number = 0
    db = get_db()
    # Get the most recently created round
    latest_round = db.execute(
        "SELECT number" " FROM round WHERE club_id = ?" " ORDER BY number DESC",
        (g.user["club_id"],),
    ).fetchone()
    # If there is one
    if latest_round:
        latest_round_number = latest_round["number"]
    db.execute(
        "INSERT INTO round (number, name, description, club_id)" " VALUES (?, ?, ?, ?)",
        (latest_round_number + 1, name, description, club_id),
    )
    db.commit()


@bp.route("/<int:id>/")
@login_required
def view(id):
    # Defines the round view screen depending on round status
    round_id = id
    round = get_round(round_id)
    db = get_db()

    club_users_count = get_club_users_count(round_id)
    song_count = get_song_count(round_id)
    guess_count = get_guess_count(round_id)

    # Get song from round with user's id
    user_song = db.execute(
        "SELECT artist, name, image_url, spotify_track_id, user_id, round_id, club_id"
        " FROM song WHERE user_id = ? AND round_id = ? AND club_id = ?",
        (g.user["id"], id, g.user["club_id"]),
    ).fetchone()

    # If users = songs (everyone has submitted)
    if get_round_status(round_id) == "open_for_guesses":
        # Get users
        users = db.execute(
            "SELECT id, username FROM user WHERE club_id = ?", (g.user["club_id"],)
        ).fetchall()

        # Get all songs
        songs = db.execute(
            "SELECT id, artist, name, image_url, spotify_track_id, user_id, round_id, club_id"
            " FROM song WHERE round_id = ? AND club_id = ? ",
            (id, g.user["club_id"]),
        ).fetchall()

        # Get songs submitted by other users
        songs_except_own = db.execute(
            "SELECT id, artist, name, image_url, spotify_track_id, user_id, round_id, club_id"
            " FROM song WHERE round_id = ? AND club_id = ? AND user_id != ? ",
            (id, g.user["club_id"], g.user["id"]),
        ).fetchall()

        # If all users have guessed
        if get_round_status(round_id) == "complete":
            # Get guesses
            guesses = db.execute(
                "SELECT id, guess_user_id, comment, user_id, song_id, round_id, club_id"
                " FROM song WHERE round_id = ? AND club_id = ? ",
                (id, g.user["club_id"]),
            ).fetchall()

            # Show results
            # Update user scores

        # Else (not everyone has guessed)
        # Show songs
        # Show link to playlist
        return render_template(
            "round/view.html",
            round=round,
            songs=songs,
            user_song=user_song,
            songs_except_own=songs_except_own,
            users=users,
            guesses=guesses,
            song_count=song_count,
            club_users_count=club_users_count,
        )

    # Else (not everyone has submitted)

    # If user has submitted
    # Show the song info
    if user_song:
        return render_template(
            "round/view.html",
            round=round,
            user_song=user_song,
            song_count=song_count,
            club_users_count=club_users_count,
        )

    # Else
    # Show the song submit form
    else:
        return render_template(
            "round/view.html",
            round=round,
            song_count=song_count,
            club_users_count=club_users_count,
        )


def refresh_access_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": CLIENT_ID_SECRET_B64,
    }

    data = {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}

    # POST request to Spotify API to request new access token. Format response as JSON
    r = requests.post(
        "https://accounts.spotify.com/api/token", headers=headers, data=data
    ).json()
    return r["access_token"]


@bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit(id):
    round_id = id
    if request.method == "POST":
        # TODO Add error handling
        spotify_track_url = request.form["spotify_track_url"]
        error = None

        if not spotify_track_url:
            error = "Spotify track URL is required."

        if error is not None:
            flash(error)
        else:
            # Get new access token for Spotify
            access_token = refresh_access_token()

            headers = {"Authorization": "Bearer {token}".format(token=access_token)}

            # Remove the start of the URL to get the track id
            spotify_track_id = spotify_track_url.replace(
                "https://open.spotify.com/track/", ""
            )

            # GET track info from Spotify. Format response as JSON
            r = requests.get(
                BASE_URL + "tracks/" + spotify_track_id, headers=headers
            ).json()

            db = get_db()
            # Add song to database
            db.execute(
                "INSERT INTO song (artist, name, image_url, spotify_track_id, user_id, round_id, club_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    r["artists"][0]["name"],
                    r["name"],
                    r["album"]["images"][0]["url"],
                    r["id"],
                    g.user["id"],
                    round_id,
                    g.user["club_id"],
                ),
            )
            db.commit()

            # If all users have submitted songs
            if get_club_users_count(round_id) == get_song_count(round_id):
                db = get_db()
                # Update round status
                db.execute(
                    "UPDATE round SET status = ?" " WHERE id = ?",
                    ("open_for_guesses", round_id),
                )
                db.commit()

                # Create playlist

                # Get round name and description
                round = get_round(round_id)
                round_name = round["name"]
                round_description = round["description"]

                headers = {
                    "Authorization": "Bearer {token}".format(token=access_token),
                    "Content-Type": "application/json",
                }
                json = {
                    "name": round_name,
                    "description": round_description,
                }

                # POST new playlist to the guesslist Spotify user. Format response as JSON
                r = requests.post(
                    BASE_URL + "users/" + SPOTIFY_USER_ID + "/playlists",
                    headers=headers,
                    json=json,
                ).json()

                playlist_id = r["id"]
                playlist_url = r["external_urls"]["spotify"]

                # Get songs for current round
                songs = get_songs_this_round(round_id)

                # List to store track URIs
                uri_list = []

                # For each song, construct the URI from the track id and append to list
                for song in songs:
                    uri_list.append("spotify:track:" + song["spotify_track_id"])

                # Randomly shuffle the list to make it more difficult for users to guess who submitted what song
                random.shuffle(uri_list)

                # Create string containing commma-separated list of URIs
                uri_string = ",".join(uri_list)

                headers = {"Authorization": "Bearer {token}".format(token=access_token)}

                # POST tracks to playlist
                r = requests.post(
                    BASE_URL
                    + "playlists/"
                    + playlist_id
                    + "/tracks?uris="
                    + uri_string,
                    headers=headers,
                )

                # Add the playlist URL to the round in the database
                db = get_db()
                db.execute(
                    "UPDATE round SET playlist_url = ?" " WHERE id = ?",
                    (playlist_url, round_id),
                )
                db.commit()

            return redirect("/round/" + str(round_id))


@bp.route("/<int:id>/guess", methods=["POST"])
@login_required
def guess(id):
    round_id = id
    club_id = g.user["club_id"]
    if request.method == "POST":
        data = request.form
        db = get_db()
        # Inputs are named '1', '2', '3' up to the number of songs guessed on
        i = 1
        while True:
            # Check if there is an input named i
            try:
                values = data[str(i)]
            except:
                # If not, break the loop
                break
            else:
                print(values)
                # The value of the input is a string containing a comma-separated list of values
                # Split that value into an array
                values_array = values.split(",")
                print(values_array)
                song_id = values_array[0]
                guess_username = values_array[1]
                guess_user_id = db.execute(
                    "SELECT id FROM user WHERE username = ?",
                    (guess_username),
                ).fetchone()["id"]
                comment = values_array[2]
                db.execute(
                    "INSERT INTO guess (guess_user_id, comment, user_id, song_id, round_id, club_id)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (guess_user_id, comment, g.user["id"], song_id, round_id, club_id),
                )
                db.commit()
                i = i + 1

        # Check if all guesses received
        # (Each user can guess on every other user's song, except their own).
        club_users_count = get_club_users_count(round_id)
        guess_count = get_guess_count(round_id)
        if guess_count == (club_users_count * club_users_count - 1):
            # Update round status
            db.execute(
                "UPDATE round SET status = ?" " WHERE id = ?",
                ("complete", round_id),
            )
            db.commit()

            # Open next round
            # Get ID of next round with status 'pending'
            next_round_id = db.execute(
                "SELECT id FROM round WHERE status = ? AND club_id = ?",
                ("pending", club_id),
            ).fetchone()["id"]
            db.execute(
                "UPDATE round SET status = ?" " WHERE id = ?",
                ("open_for_songs", next_round_id),
            )
            db.commit()

        return redirect("/round/" + str(round_id))


@bp.route("/<int:id>/start")
@login_required
def start(id):
    # For the admin to start the first round in a club
    round_id = id
    db = get_db()
    db.execute(
        "UPDATE round SET status = ?" " WHERE id = ?",
        ("open_for_songs", round_id),
    )
    db.commit()

    return redirect(url_for("index.index"))


def get_club_users_count(round_id):
    # Get count of users in club
    db = get_db()
    club_users_count = db.execute(
        "SELECT COUNT(*) FROM user WHERE club_id = ?", (g.user["club_id"],)
    ).fetchone()["COUNT(*)"]
    return club_users_count


def get_round(id):
    current_round = (
        get_db()
        .execute(
            "SELECT id, name, description, created, status, playlist_url, club_id"
            " FROM round"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if current_round is None:
        abort(404, f"round id {id} doesn't exist.")

    return current_round


def get_round_status(round_id):
    db = get_db()
    round_status = db.execute(
        "SELECT status FROM round WHERE id = ?", (round_id,)
    ).fetchone()["status"]
    return round_status


def get_song_count(round_id):
    # Get count of songs in round
    db = get_db()
    song_count = db.execute(
        "SELECT COUNT(*) FROM song WHERE club_id = ? and round_id = ?",
        (g.user["club_id"], round_id),
    ).fetchone()["COUNT(*)"]
    return song_count


def get_songs_this_round(round_id):
    db = get_db()
    songs = db.execute(
        "SELECT spotify_track_id" " FROM song WHERE round_id = ? AND club_id = ? ",
        (round_id, g.user["club_id"]),
    ).fetchall()
    return songs


def get_guess_count(round_id):
    # Get count of songs in round
    db = get_db()
    guess_count = db.execute(
        "SELECT COUNT(*) FROM guess WHERE club_id = ? and round_id = ?",
        (g.user["club_id"], round_id),
    ).fetchone()["COUNT(*)"]
    return guess_count


# @bp.route("/<int:id>/update", methods=("GET", "POST"))
# @login_required
# def update(id):
#     round = get_round(id)

#     if request.method == "POST":
#         name = request.form["name"]
#         error = None

#         if not name:
#             error = "round name is required."

#         if error is not None:
#             flash(error)
#         else:
#             db = get_db()
#             db.execute("UPDATE round SET name = ?" " WHERE id = ?", (name, id))
#             db.commit()
#             return redirect(url_for("index.index"))

#     return render_template("round/update.html", round=round)


# @bp.route("/<int:id>/delete", methods=("POST",))
# @login_required
# def delete(id):
#     get_round(id)
#     db = get_db()
#     db.execute("DELETE FROM round WHERE id = ?", (id,))
#     db.commit()
#     return redirect(url_for("round.index"))
