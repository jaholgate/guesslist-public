from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db
from guesslist.utilities import get_club, get_rounds
from guesslist.round import add_round

bp = Blueprint("club", __name__, url_prefix="/club")


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        name = request.form["name"]
        error = None

        if not name:
            error = "Club name is required."

        if g.user["club_id"]:
            error = "You are already in a club."

        if error is not None:
            flash(error)
        else:
            user_id = g.user["id"]
            db = get_db()

            # Check if any clubs have been created yet
            clubs = db.execute(
                "SELECT COUNT(*) FROM club",
            ).fetchone()["COUNT(*)"]
            print(clubs)

            # If not, start round IDs from 1000 to avoid duplication of club IDs
            if clubs == 0:
                print("updating seq")
                db.execute(
                    "INSERT INTO sqlite_sequence (name, seq)" " VALUES (?, ?)",
                    ("round", 1000),
                )
                db.commit()

            db.execute(
                "INSERT INTO club (name, admin_id)" " VALUES (?, ?)",
                (name, user_id),
            )
            db.commit()
            club = db.execute(
                "SELECT club.id"
                " FROM club JOIN user ON club.admin_id = user.id"
                " WHERE user.id = ?",
                (user_id,),
            ).fetchone()
            db.execute(
                "UPDATE user SET club_id = ?" " WHERE id = ?", (club[0], user_id)
            )
            db.commit()

            starter_rounds = [
                {"name": "Y2K", "description": "Songs released 1999-2001"},
                {"name": "Tree Hugger", "description": "Songs mentioning nature"},
                {
                    "name": "Cover Up",
                    "description": "Songs that are a cover of another song",
                },
                {"name": "Road Trip", "description": "Songs about cars or driving"},
                {"name": "Hello, Numan", "description": "Best of Gary"},
            ]

            for starter_round in starter_rounds:
                add_round(
                    starter_round["name"],
                    starter_round["description"],
                    club[0],
                )

            return redirect(url_for("index.index"))

    return render_template("club/create.html")


@bp.route("/join", methods=("GET", "POST"))
@login_required
def join():
    if request.method == "POST":
        club_id = request.form["club_id"]
        error = None

        if not club_id:
            error = "Club ID is required."

        if g.user["club_id"]:
            error = "You are already in a club."

        if error is not None:
            flash(error)
        else:
            # TODO: refactor this, as it is repeated in auth.py
            # Check if club id exists
            db = get_db()
            club_id_check = db.execute(
                "SELECT id, accepting_members FROM club WHERE id = ?",
                (club_id,),
            ).fetchone()
            if not club_id_check:
                error = "Club ID was not found."
            elif club_id_check["accepting_members"] == 0:
                error = "The club you entered is not accepting members."
            else:
                # If true, add club_id to user record
                db.execute(
                    "UPDATE user SET club_id = ?" " WHERE id = ?",
                    (club_id, g.user["id"]),
                )
                db.commit()

            if error is not None:
                flash(error)

            else:
                return redirect(url_for("index.index"))

    return render_template("club/join.html")


@bp.route("/<int:id>/leaderboard")
@login_required
def leaderboard(id):
    club_id = id
    club = get_club(club_id)
    users = (
        get_db()
        .execute(
            "SELECT username, score FROM user WHERE club_id = ? ORDER BY score DESC",
            (club_id,),
        )
        .fetchall()
    )

    return render_template("club/leaderboard.html", club=club, users=users)


@bp.route("/<int:id>/manage", methods=("GET", "POST"))
@login_required
def manage(id):
    club = get_club(id)
    rounds = get_rounds()

    if request.method == "POST":
        name = request.form["name"]
        error = None

        if not name:
            error = "Club name is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute("UPDATE club SET name = ?" " WHERE id = ?", (name, id))
            db.commit()
            return redirect(url_for("index.index"))

    return render_template("club/manage.html", club=club, rounds=rounds)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_club(id)
    db = get_db()
    db.execute("DELETE FROM club WHERE id = ?", (id,))
    # TODO remove club_id from all users in club?
    db.commit()
    return redirect(url_for("index.index"))
