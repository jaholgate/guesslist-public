from flask import current_app, g
from flask_mail import Message
from guesslist import mail
from guesslist.db import get_db


def send_mail(subject, html, recipients):
    msg = Message(subject=subject, html=html, recipients=recipients)
    mail.send(msg)


def get_club(club_id):
    club = (
        get_db()
        .execute(
            "SELECT * FROM club WHERE club.id = ?",
            (club_id,),
        )
        .fetchone()
    )

    # if club is None:
    #     abort(404, f"Club id {club_id} doesn't exist.")

    # if check_author and club["admin_id"] != g.user["id"]:
    #     abort(403)

    return club


def get_club_users_count(round_id):
    # Get count of users in club
    db = get_db()
    club_users_count = db.execute(
        "SELECT COUNT(*) FROM user WHERE club_id = ?", (g.user["club_id"],)
    ).fetchone()["COUNT(*)"]
    return club_users_count


def get_round(round_id):
    current_round = (
        get_db()
        .execute(
            "SELECT * FROM round WHERE id = ?",
            (round_id,),
        )
        .fetchone()
    )

    if current_round is None:
        abort(404, f"round id {round_id} doesn't exist.")

    return current_round


def get_rounds():
    db = get_db()
    rounds = db.execute(
        "SELECT * FROM round WHERE club_id = ?",
        (g.user["club_id"],),
    ).fetchall()
    return rounds


def get_round_status(round_id):
    db = get_db()
    round_status = db.execute(
        "SELECT status FROM round WHERE id = ?", (round_id,)
    ).fetchone()["status"]
    return round_status


def get_song_count(round_id):
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


# Number of users who have guessed in the current round
def get_user_guess_count(round_id):
    db = get_db()
    user_guess_count = db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM guess WHERE club_id = ? and round_id = ?",
        (g.user["club_id"], round_id),
    ).fetchone()["COUNT(DISTINCT user_id)"]
    return user_guess_count


# Total number of guesses in the current round
def get_guess_count(round_id):
    db = get_db()
    guess_count = db.execute(
        "SELECT COUNT(*) FROM guess WHERE club_id = ? and round_id = ?",
        (g.user["club_id"], round_id),
    ).fetchone()["COUNT(*)"]
    return guess_count


def join_club(club_id, user_id, source):
    # Check if club id exists
    db = get_db()
    error = None
    club_id_check = db.execute(
        "SELECT id, accepting_members FROM club WHERE id = ?",
        (club_id,),
    ).fetchone()
    if not club_id_check:
        # Set relevant error message depending on what page they are joining from
        if source == "register":
            error = "Successfully registered, but your club ID was not found."
        else:
            error = "Club ID was not found."
    elif club_id_check["accepting_members"] == 0:
        error = "The club you entered is not accepting members."
    else:
        # If true, add club_id to user record
        db.execute(
            "UPDATE user SET club_id = ?" " WHERE id = ?",
            (club_id, user_id),
        )
        db.commit()

    if error is not None:
        flash(error)

    else:
        return
