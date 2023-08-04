import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.security import check_password_hash, generate_password_hash

from guesslist import hashids
from guesslist.db import get_db
from guesslist.utilities import (
    join_club,
    send_mail,
    get_reset_token,
    verify_reset_token,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        # User will pass in a hashid - 6-character code e.g. ABC123 so we need to decode it.
        club_id = hashids.decode(request.form["club"])

        error = None

        if not email:
            error = "Email is required."
        elif not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO user (email, username, password) VALUES (?, ?, ?)",
                    (email, username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"Username {username}, or your email address, is already registered."
            else:
                user = db.execute(
                    "SELECT * FROM user WHERE email = ?", (email,)
                ).fetchone()

                # If the user registered with a club id, add club id to user i.e. join that club
                if club_id:
                    join_club(club_id, user["id"], "register")

                # Log the user in
                session.clear()
                session["user_id"] = user["id"]
                if error:
                    flash(error)
                return redirect(url_for("index"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        error = None
        user = db.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

        if user is None:
            error = "Email address not recognised."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/reset", methods=("GET", "POST"))
def reset():
    if request.method == "POST":
        email = request.form["email"]
        db = get_db()
        error = None
        user = db.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

        if user is None:
            error = "Email address not recognised."

        if error is None:
            token = get_reset_token(user["username"])
            url = url_for("auth.reset_verified", _external=True, token=token)

            send_mail(
                "Reset your password",
                f"<p>Use this link to reset your guesslist password:</p><p><a href='{url}'></a>{url}</p>",
                [user["email"]],
            )
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/reset.html")


@bp.route("/reset-verified/<token>", methods=("GET", "POST"))
def reset_verified(token):
    user = verify_reset_token(token)
    if request.method == "GET":
        if user:
            return render_template("auth/reset_verified.html")
        else:
            return redirect(url_for("index"))

    if request.method == "POST":
        password = request.form["password"]
        db = get_db()
        db.execute(
            "UPDATE user SET password = ? WHERE id = ?",
            (generate_password_hash(password), user["id"]),
        )
        db.commit()

        return redirect(url_for("auth.login"))


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
