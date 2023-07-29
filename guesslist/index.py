from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db

bp = Blueprint("index", __name__)


@bp.route("/")
def index():
    if g.user and g.user["club_id"]:
        db = get_db()
        club = db.execute(
            "SELECT id, name, admin_id FROM club WHERE id = ?", (g.user["club_id"],)
        ).fetchone()
        rounds = get_rounds()
        return render_template("index.html", club=club, rounds=rounds)
    else:
        return render_template("index.html")


def get_rounds():
    db = get_db()
    rounds = db.execute(
        "SELECT id, name, description, status, created, club_id"
        " FROM round WHERE club_id = ?",
        (g.user["club_id"],),
    ).fetchall()
    return rounds
