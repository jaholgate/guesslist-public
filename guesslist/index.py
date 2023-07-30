from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from guesslist.auth import login_required
from guesslist.db import get_db
from guesslist.utilities import get_club, get_club_users_count
from guesslist.utilities import get_rounds

bp = Blueprint("index", __name__)


@bp.route("/")
def index():
    if g.user and g.user["club_id"]:
        club = get_club(g.user["club_id"])
        rounds = get_rounds()
        club_users_count = get_club_users_count(g.user["club_id"])
        return render_template(
            "index.html", club=club, rounds=rounds, club_users_count=club_users_count
        )
    else:
        return render_template("index.html")
