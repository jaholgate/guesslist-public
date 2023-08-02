from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
import base64
import requests
import random
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db
from guesslist.utilities import (
    get_club,
    get_round,
    get_round_status,
    get_club_users_count,
    get_song_count,
    get_songs_this_round,
    get_user_guess_count,
)

bp = Blueprint("round", __name__, url_prefix="/round")


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add():
    club = get_club(g.user["id"])
    if g.user["id"] != club["admin_id"]:
        return redirect(url_for("index.index"))

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

    return render_template("round/add.html", club=club)


def add_round(name, description, club_id):
    db = get_db()
    db.execute(
        "INSERT INTO round (name, description, club_id)" " VALUES (?, ?, ?)",
        (name, description, club_id),
    )
    db.commit()


@bp.route("/<hashid:id>/")
@login_required
def view(id):
    # Defines the round view screen depending on round status

    db = get_db()

    # Variables for render_template
    club = get_club(g.user["id"])
    round_id = id
    round = get_round(round_id)
    songs = {}
    user_song = {}
    songs_except_own = {}
    users = {}
    guesses = {}
    user_guess = {}
    round_points = {}
    club_users_count = get_club_users_count(round_id)
    song_count = get_song_count(round_id)
    user_guess_count = get_user_guess_count(round_id)

    # Get song from round with user's id
    user_song = db.execute(
        "SELECT artist, name, image_url, spotify_track_id, user_id, round_id, club_id"
        " FROM song WHERE user_id = ? AND round_id = ? AND club_id = ?",
        (g.user["id"], round_id, g.user["club_id"]),
    ).fetchone()

    # If users = songs (everyone has submitted)
    if get_round_status(round_id) == "open_for_guesses":
        # Get users
        users = db.execute(
            "SELECT id, username FROM user WHERE club_id = ?", (g.user["club_id"],)
        ).fetchall()

        # Get songs submitted by other users
        songs_except_own = db.execute(
            "SELECT id, artist, name, image_url, spotify_track_id, user_id, round_id, club_id"
            " FROM song WHERE round_id = ? AND club_id = ? AND user_id != ? ",
            (round_id, g.user["club_id"], g.user["id"]),
        ).fetchall()
        # Randomly shuffle the list to make it more difficult for users to guess who submitted what song
        random.shuffle(songs_except_own)

        # Check if user has guessed
        user_guess = db.execute(
            "SELECT user_id"
            " FROM guess WHERE user_id = ? AND round_id = ? AND club_id = ?",
            (g.user["id"], round_id, g.user["club_id"]),
        ).fetchone()

    # If all users have guessed
    if get_round_status(round_id) == "complete":
        # Get all songs
        songs = db.execute(
            "SELECT song.id, artist, name, image_url, spotify_track_id, user_id, round_id, song.club_id, username"
            " FROM song "
            " JOIN user ON song.user_id = user.id"
            " WHERE song.round_id = ? AND song.club_id = ?",
            (round_id, g.user["club_id"]),
        ).fetchall()

        # Get guesses
        guesses = db.execute(
            "SELECT guess.id, guess_user_id, guess_username, comment, user_id, song_id, round_id, guess.club_id, username"
            " FROM guess "
            " JOIN user ON user_id = user.id"
            " WHERE round_id = ? AND guess.club_id = ? ",
            (round_id, g.user["club_id"]),
        ).fetchall()

        # for guess in guesses {
        #     if guess['user_id'] not in round_points:
        #        round_points['user_id'] =
        # }

        round_points = db.execute(
            "SELECT username, SUM(points) as points"
            " FROM guess "
            " JOIN user ON user_id = user.id"
            " WHERE round_id = ? AND guess.club_id = ? "
            " GROUP BY username "
            " ORDER BY points DESC",
            (round_id, g.user["club_id"]),
        ).fetchall()

    return render_template(
        "round/view.html",
        club=club,
        round=round,
        songs=songs,
        user_song=user_song,
        songs_except_own=songs_except_own,
        users=users,
        user_guess=user_guess,
        guesses=guesses,
        round_points=round_points,
        song_count=song_count,
        club_users_count=club_users_count,
        user_guess_count=user_guess_count,
    )


def refresh_access_token():
    with current_app.app_context():
        CLIENT_ID_SECRET_B64 = (
            "Basic "
            + base64.b64encode(
                (
                    current_app.config["CLIENT_ID"]
                    + ":"
                    + current_app.config["CLIENT_SECRET"]
                ).encode()
            ).decode()
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": CLIENT_ID_SECRET_B64,
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": current_app.config["REFRESH_TOKEN"],
        }

    # POST request to Spotify API to request new access token. Format response as JSON
    r = requests.post(
        "https://accounts.spotify.com/api/token", headers=headers, data=data
    ).json()
    return r["access_token"]


@bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit(id):
    if request.method == "POST":
        round_id = id
        spotify_track_url = request.form["spotify_track_url"]
        db = get_db()
        error = None

        if not spotify_track_url:
            error = "Spotify track URL is required."

        # Remove the start of the URL and any query params to get the track id
        spotify_track_id = spotify_track_url.replace(
            "https://open.spotify.com/track/", ""
        ).split("?")[0]

        # If song already submitted, or user has already submitted, return an error
        song_already_in_round = db.execute(
            "SELECT id FROM song WHERE spotify_track_id = ? AND round_id = ?",
            (spotify_track_id, round_id),
        ).fetchone()

        if song_already_in_round:
            error = "This song has already been submitted in this round."

        user_already_in_round = db.execute(
            "SELECT id FROM song WHERE user_id = ? AND round_id = ?",
            (g.user["id"], round_id),
        ).fetchone()

        if user_already_in_round:
            error = "You have already submitted a song in this round."

        if error is not None:
            flash(error)
            return redirect(url_for("round.view", id=round_id))

        else:
            # Get new access token for Spotify
            access_token = refresh_access_token()
            BASE_URL = "https://api.spotify.com/v1/"
            headers = {"Authorization": "Bearer {token}".format(token=access_token)}

            # GET track info from Spotify. Format response as JSON
            r = requests.get(
                BASE_URL + "tracks/" + spotify_track_id, headers=headers
            ).json()

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
                with current_app.app_context():
                    r = requests.post(
                        BASE_URL
                        + "users/"
                        + current_app.config["SPOTIFY_USER_ID"]
                        + "/playlists",
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

            return redirect(url_for("round.view", id=round_id))


@bp.route("/<hashid:id>/guess", methods=["POST"])
@login_required
def guess(id):
    if request.method == "POST":
        round_id = id
        club_id = g.user["club_id"]
        data = request.form
        db = get_db()
        error = None

        print(data)
        # If user already guessed, reject
        user_already_guessed = db.execute(
            "SELECT id FROM guess WHERE user_id = ? AND round_id = ?",
            (g.user["id"], round_id),
        ).fetchone()

        if user_already_guessed:
            error = "You have already submitted your guesses."

        if error is not None:
            flash(error)
            return redirect(url_for("round.view", id=round_id))

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
                # The value of the input is a string containing a comma-separated list of values
                # Split that value into an array
                values_array = values.split(",")
                song_id = values_array[0]
                guess_username = values_array[1]
                guess_user_id = db.execute(
                    "SELECT id FROM user WHERE username = ?",
                    (guess_username,),
                ).fetchone()["id"]
                comment = values_array[2]
                song_submitter_id = db.execute(
                    "SELECT user_id FROM song WHERE id = ?",
                    (song_id),
                ).fetchone()["user_id"]
                points = 0
                if guess_user_id == song_submitter_id:
                    points = 1
                db.execute(
                    "INSERT INTO guess (guess_user_id, guess_username, comment, points, user_id, song_id, round_id, club_id)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        guess_user_id,
                        guess_username,
                        comment,
                        points,
                        g.user["id"],
                        song_id,
                        round_id,
                        club_id,
                    ),
                )
                db.commit()
                i = i + 1

        # Check if all users have guessed
        club_users_count = get_club_users_count(round_id)
        user_guess_count = get_user_guess_count(round_id)
        if club_users_count == user_guess_count:
            # Update round status
            db.execute(
                "UPDATE round SET status = ?" " WHERE id = ?",
                ("complete", round_id),
            )
            db.commit()

            # Update scores

            # Get users
            users = db.execute(
                "SELECT id FROM user WHERE club_id = ?", (g.user["club_id"],)
            ).fetchall()

            # For each user
            for user in users:
                user_id = user["id"]
                # Get the number of points scored in this round
                round_points = db.execute(
                    "SELECT SUM(points) FROM guess WHERE user_id = ? AND round_id = ?",
                    (user_id, round_id),
                ).fetchone()["SUM(points)"]
                # Add points to their overall score
                db.execute(
                    "UPDATE user SET score = score + ? WHERE id = ?",
                    (round_points, user_id),
                )
                db.commit()

            # Open next round
            # Get ID of next round with status 'pending'
            next_round_id = db.execute(
                "SELECT id FROM round WHERE status = ? AND club_id = ?",
                ("pending", club_id),
            ).fetchone()["id"]
            # Update round status
            db.execute(
                "UPDATE round SET status = ?" " WHERE id = ?",
                ("open_for_songs", next_round_id),
            )
            db.commit()

        return redirect(url_for("round.view", id=round_id))


@bp.route("/<hashid:id>/start")
@login_required
def start(id):
    # For the admin to start the first round in a club
    round_id = id
    club_id = g.user["club_id"]
    db = get_db()
    db.execute(
        "UPDATE round SET status = ?" " WHERE id = ?",
        ("open_for_songs", round_id),
    )
    db.execute(
        "UPDATE club SET accepting_members = ?" " WHERE id = ?",
        (0, club_id),
    )
    db.commit()

    return redirect(url_for("index.index"))


@bp.route("/<hashid:id>/manage", methods=("GET", "POST"))
@login_required
def manage(id):
    round = get_round(id)

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]

        error = None

        if not name:
            error = "round name is required."

        if not description:
            error = "round name is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE round SET name = ?, description = ?" " WHERE id = ?",
                (name, description, id),
            )
            db.commit()
            return redirect(url_for("index.index"))

    return render_template("round/manage.html", round=round)


@bp.route("/<hashid:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_round(id)
    db = get_db()
    db.execute("DELETE FROM round WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("index.index"))
