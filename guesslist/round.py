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
import requests
import random
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db
from guesslist.utilities import (
    get_club,
    get_round,
    get_round_status,
    get_rounds_pending,
    get_rounds_open,
    get_club_users,
    get_club_users_count,
    get_song_count,
    get_songs_this_round,
    get_user_guess_count,
    send_mail,
    refresh_access_token,
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
        "SELECT * FROM song WHERE user_id = ? AND round_id = ? AND club_id = ?",
        (g.user["id"], round_id, g.user["club_id"]),
    ).fetchone()

    # If users = songs (everyone has submitted)
    if get_round_status(round_id) == "open_for_guesses":
        # Get users
        users = get_club_users()

        # Get songs submitted by other users
        songs_except_own = db.execute(
            "SELECT *"
            " FROM song"
            " WHERE round_id = ? AND club_id = ? AND user_id != ? ",
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
            "SELECT song.id, artist, name, image_url, spotify_track_id, comment, user_id, round_id, song.club_id, username"
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


@bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit(id):
    if request.method == "POST":
        round_id = id
        spotify_track_url = request.form["spotify_track_url"]
        comment = request.form["comment"]
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
            r = requests.get(BASE_URL + "tracks/" + spotify_track_id, headers=headers)

            if r.status_code != 200:
                error = "Track not found. Please make sure you entered a valid Spotify track URL."
                flash(error)
                return redirect(url_for("round.view", id=round_id))

            r = r.json()

            # Add song to database
            db.execute(
                "INSERT INTO song (artist, name, image_url, spotify_track_id, comment, user_id, round_id, club_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["artists"][0]["name"],
                    r["name"],
                    r["album"]["images"][0]["url"],
                    r["id"],
                    comment,
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

                # TODO unfollow playlist once done (doesn't delete the playlist itself from Spotify)
                # https://developer.spotify.com/documentation/web-api/reference/unfollow-playlist
                # headers = {"Authorization": "Bearer {token}".format(token=access_token)}

                # r = requests.delete(
                #     BASE_URL + "playlists/" + playlist_id + "followers",
                #     headers=headers,
                # )

                # Add the playlist URL to the round in the database
                db = get_db()
                db.execute(
                    "UPDATE round SET playlist_url = ?" " WHERE id = ?",
                    (playlist_url, round_id),
                )
                db.commit()

                users = get_club_users()

                for user in users:
                    send_mail(
                        f"New playlist ready: {round_name}",
                        f"<p><a href='{request.host_url}'>Open guesslist</a> to listen to the playlist and submit your guesses.</p>",
                        [user["email"]],
                    )

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
            users = get_club_users()

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

                round_name = get_round(round_id)["name"]

                send_mail(
                    f"The guesses are in: {round_name}",
                    f"<p><a href='{request.host_url}'>Open guesslist</a> to see how you did, and submit your song for the next round.</p>",
                    [user["email"]],
                )

            # Open next round
            # Get ID of next round with status 'pending'
            next_round_id = db.execute(
                "SELECT id FROM round WHERE status = ? AND club_id = ?",
                ("pending", club_id),
            ).fetchone()["id"]
            if next_round_id:
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

    users = get_club_users()
    for user in users:
        send_mail(
            f"The first round is starting!",
            f"<p><a href='{request.host_url}'>Open guesslist</a> to submit your song.</p>",
            [user["email"]],
        )

    return redirect(url_for("index.index"))


@bp.route("/<hashid:id>/manage", methods=("GET", "POST"))
@login_required
def manage(id):
    round_id = id
    round = get_round(round_id)

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
                (name, description, round_id),
            )
            db.commit()
            return redirect(url_for("index.index"))

    rounds_open = get_rounds_open()
    rounds_pending = get_rounds_pending()
    club_accepting_members = get_club(g.user["id"])["accepting_members"]
    # If this is the next pending round (there are no open rounds in the club and the club is not accepting members i.e. game has started previously), pass this to the template so we can show 'open round' button
    if (
        not rounds_open
        and rounds_pending[0]["id"] == round_id
        and club_accepting_members == 0
    ):
        is_next_round = True

        return render_template(
            "round/manage.html", round=round, is_next_round=is_next_round
        )
    else:
        return render_template("round/manage.html", round=round)


@bp.route("/<hashid:id>/open")
@login_required
def open(id):
    round = get_round(id)

    if round["status"] == "pending":
        db = get_db()
        db.execute(
            "UPDATE round SET status = ?" " WHERE id = ?",
            ("open_for_songs", id),
        )
        db.commit()
        return redirect(url_for("index.index"))

    else:
        return render_template("round/manage.html", round=round)


@bp.route("/<hashid:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_round(id)
    db = get_db()
    db.execute("DELETE FROM round WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("index.index"))
