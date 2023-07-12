from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db

bp = Blueprint("club", __name__, url_prefix="/club")


@bp.route("/")
def index():
    db = get_db()
    clubs = db.execute(
        "SELECT club.id, name, created, admin_id, username"
        " FROM club JOIN user ON club.admin_id = user.id"
        " ORDER BY created DESC"
    ).fetchall()
    rounds = db.execute(
        "SELECT round.id, number, round.name, description, round.created, starts, ends, admin_id"
        " FROM round JOIN club ON round.club_id = club.id"
        " ORDER BY number ASC"
    ).fetchall()
    return render_template("club/index.html", clubs=clubs, rounds=rounds)


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
            db = get_db()
            db.execute(
                "INSERT INTO club (name, admin_id)" " VALUES (?, ?)",
                (name, g.user["id"]),
            )
            db.commit()
            club = (
                get_db()
                .execute(
                    "SELECT club.id"
                    " FROM club JOIN user ON club.admin_id = user.id"
                    " WHERE user.id = ?",
                    (g.user["id"],),
                )
                .fetchone()
            )
            db.execute(
                "UPDATE user SET club_id = ?" " WHERE id = ?", (club[0], g.user["id"])
            )
            db.commit()
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
            return redirect(url_for("club.index"))

    return render_template("club/update.html", club=club)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_club(id)
    db = get_db()
    db.execute("DELETE FROM club WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("club.index"))
