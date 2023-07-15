from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db
from guesslist.round import add_round

bp = Blueprint("club", __name__, url_prefix="/club")


# @bp.route("/")
# def index():
#     db = get_db()
#     clubs = db.execute(
#         "SELECT club.id, name, created, admin_id, username"
#         " FROM club JOIN user ON club.admin_id = user.id"
#         " ORDER BY created DESC"
#     ).fetchall()
#     rounds = db.execute(
#         "SELECT round.id, number, round.name, description, round.created, admin_id"
#         " FROM round JOIN club ON round.club_id = club.id"
#         " ORDER BY number ASC"
#     ).fetchall()
#     return render_template("club/index.html", clubs=clubs, rounds=rounds)


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

            # TODO fix round numbering - currently '1' for each round created
            for starter_round in starter_rounds:
                add_round(
                    starter_round["name"],
                    starter_round["description"],
                    user_id,
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
            club = (
                get_db()
                .execute(
                    "SELECT id" " FROM club " " WHERE id = ?",
                    (club_id,),
                )
                .fetchone()
            )
            if not club:
                error = "Club not found."
            if error is not None:
                flash(error)
            else:
                db = get_db()
                db.execute(
                    "UPDATE user SET club_id = ?" " WHERE id = ?",
                    (club_id, g.user["id"]),
                )
                db.commit()
                return redirect(url_for("index.index"))

    return render_template("club/join.html")


def get_club(id, check_author=True):
    club = (
        get_db()
        .execute(
            "SELECT club.id, name, created, admin_id, username"
            " FROM club JOIN user ON club.admin_id = user.id"
            " WHERE club.id = ?",
            (id,),
        )
        .fetchone()
    )

    if club is None:
        abort(404, f"Club id {id} doesn't exist.")

    if check_author and club["admin_id"] != g.user["id"]:
        abort(403)

    return club


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    club = get_club(id)

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

    return render_template("club/update.html", club=club)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_club(id)
    db = get_db()
    db.execute("DELETE FROM club WHERE id = ?", (id,))
    # TODO remove club_id from all users in club?
    db.commit()
    return redirect(url_for("index.index"))
