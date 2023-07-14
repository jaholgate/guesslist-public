from flask import Blueprint, flash, g, redirect, render_template, request, url_for
import requests
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db

bp = Blueprint("round", __name__, url_prefix="/round")

CLIENT_ID = "***REMOVED***"
CLIENT_SECRET = "***REMOVED***"


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add():
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
            latest_round_number = 0
            db = get_db()
            latest_round = db.execute(
                "SELECT number" " FROM round WHERE club_id = ?" " ORDER BY number DESC",
                (g.user["club_id"],),
            ).fetchone()
            if latest_round:
                latest_round_number = latest_round["number"]
            db.execute(
                "INSERT INTO round (number, name, description, club_id)"
                " VALUES (?, ?, ?, ?)",
                (latest_round_number + 1, name, description, g.user["club_id"]),
            )
            db.commit()
            return redirect(url_for("index.index"))

    return render_template("round/add.html")


def get_round(id):
    current_round = (
        get_db()
        .execute(
            "SELECT id, name, description, created, status, club_id"
            " FROM round"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if current_round is None:
        abort(404, f"round id {id} doesn't exist.")

    return current_round


def get_club_users_count(round_id):
    # Get count of users in club
    db = get_db()
    club_users_count = db.execute(
        "SELECT COUNT(*) FROM user WHERE club_id = ?", (g.user["club_id"],)
    ).fetchone()["COUNT(*)"]
    return club_users_count


def get_song_count(round_id):
    # Get count of songs in round
    db = get_db()
    song_count = db.execute(
        "SELECT COUNT(*) FROM song WHERE club_id = ? and round_id = ?",
        (g.user["club_id"], round_id),
    ).fetchone()["COUNT(*)"]
    return song_count


def get_round_status(round_id):
    db = get_db()
    round_status = db.execute(
        "SELECT status FROM round WHERE id = ?", (round_id,)
    ).fetchone()["status"]
    return round_status


@bp.route("/<int:id>/")
@login_required
def view(id):
    round_id = id
    round = get_round(round_id)
    db = get_db()

    club_users_count = get_club_users_count(round_id)
    song_count = get_song_count(round_id)

    # If users = songs (everyone has submitted)
    if get_round_status(round_id) == "open_for_guesses":
        # Get songs
        songs = db.execute(
            "SELECT artist, name, image_url, spotify_external_url, user_id, round_id, club_id"
            " FROM song WHERE round_id = ? AND club_id = ? ",
            (id, g.user["club_id"]),
        ).fetchall()

        # Get guess count

        # If guesses = songs (everyone has guessed)
        # Get guesses
        # Show results

        # Else (not everyone has guessed)

        # Show songs
        # Show link to playlist
        return render_template(
            "round/view.html",
            round=round,
            songs=songs,
            song_count=song_count,
            club_users_count=club_users_count,
        )

    # Else (not everyone has submitted)

    # Get song from round with user's id
    user_song = db.execute(
        "SELECT artist, name, image_url, spotify_external_url, user_id, round_id, club_id"
        " FROM song WHERE user_id = ? AND round_id = ? AND club_id = ?",
        (g.user["id"], id, g.user["club_id"]),
    ).fetchone()

    # If exists
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


@bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit(id):
    round_id = id
    if request.method == "POST":
        spotify_external_url = request.form["spotify_external_url"]
        error = None

        if not spotify_external_url:
            error = "Spotify track URL is required."

        if error is not None:
            flash(error)
        else:
            AUTH_URL = "https://accounts.spotify.com/api/token"
            auth_response = requests.post(
                AUTH_URL,
                {
                    "grant_type": "client_credentials",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                },
            )

            # convert the response to JSON
            auth_response_data = auth_response.json()

            # save the access token
            access_token = auth_response_data["access_token"]

            headers = {"Authorization": "Bearer {token}".format(token=access_token)}

            # base URL of all Spotify API endpoints
            BASE_URL = "https://api.spotify.com/v1/"

            spotify_track_id = spotify_external_url.replace(
                "https://open.spotify.com/track/", ""
            )

            r = requests.get(BASE_URL + "tracks/" + spotify_track_id, headers=headers)
            r = r.json()

            db = get_db()
            db.execute(
                "INSERT INTO song (artist, name, image_url, spotify_track_id, spotify_external_url, user_id, round_id, club_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["artists"][0]["name"],
                    r["name"],
                    r["album"]["images"][0]["url"],
                    spotify_track_id,
                    spotify_external_url,
                    g.user["id"],
                    round_id,
                    g.user["club_id"],
                ),
            )
            db.commit()

            if get_club_users_count(round_id) == get_song_count(round_id):
                db = get_db()
                db.execute(
                    "UPDATE round SET status = ?" " WHERE id = ?",
                    ("open_for_guesses", round_id),
                )
                db.commit()

            return redirect("/round/" + str(round_id))


@bp.route("/<int:id>/start")
@login_required
def start(id):
    round_id = id
    db = get_db()
    db.execute(
        "UPDATE round SET status = ?" " WHERE id = ?",
        ("open_for_songs", round_id),
    )
    db.commit()

    return redirect(url_for("index.index"))


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
