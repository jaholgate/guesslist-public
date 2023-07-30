from flask import current_app, g
from guesslist.db import get_db


def get_club(club_id):
    club = (
        get_db()
        .execute(
            "SELECT club.id, name, accepting_members, club.created, admin_id, username"
            " FROM club JOIN user ON club.admin_id = user.id"
            " WHERE club.id = ?",
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
            "SELECT id, name, description, created, status, playlist_url, club_id"
            " FROM round"
            " WHERE id = ?",
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
        "SELECT id, name, description, status, created, club_id"
        " FROM round WHERE club_id = ?",
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
