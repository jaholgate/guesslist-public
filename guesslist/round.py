from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db

bp = Blueprint("round", __name__, url_prefix="/round")


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
            db = get_db()
            db.execute(
                "INSERT INTO round (name, description, club_id)" " VALUES (?, ?, ?)",
                (name, description, g.user["club_id"]),
            )
            db.commit()
            return redirect(url_for("index.index"))

    return render_template("round/add.html")


def get_round(id):
    round = (
        get_db()
        .execute(
            "SELECT id, name, description, created, club_id"
            " FROM round"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if round is None:
        abort(404, f"round id {id} doesn't exist.")

    return round


@bp.route("/<int:id>/", methods=("GET", "POST"))
@login_required
def view(id):
    round = get_round(id)

    # if request.method == "POST":
    #     name = request.form["name"]
    #     error = None

    #     if not name:
    #         error = "round name is required."

    #     if error is not None:
    #         flash(error)
    #     else:
    #         db = get_db()
    #         db.execute("UPDATE round SET name = ?" " WHERE id = ?", (name, id))
    #         db.commit()
    #         return redirect(url_for("index.index"))

    return render_template("round/view.html", round=round)


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
