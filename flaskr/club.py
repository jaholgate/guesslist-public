from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("club", __name__, url_prefix="/club")


@bp.route("/")
def index():
    db = get_db()
    clubs = db.execute(
        "SELECT club.id, name, created, admin_id, username"
        " FROM club JOIN user ON club.admin_id = user.id"
        " ORDER BY created DESC"
    ).fetchall()
    return render_template("club/index.html", clubs=clubs)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        name = request.form["name"]
        error = None

        if not name:
            error = "Club name is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO club (name, admin_id)" " VALUES (?, ?)",
                (name, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("club.index"))

    return render_template("club/create.html")


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
            db.execute("UPDATE club SET name = ?" " WHERE id = ?", (club, id))
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
