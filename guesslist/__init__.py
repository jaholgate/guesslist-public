import os

from flask import Flask
from flask_hashids import HashidMixin, Hashids


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "guesslist.sqlite"),
        HASHIDS_ALPHABET="ABCDEFGHIJKLMNPQRSTUVWXYZ123456789",
        HASHIDS_MIN_LENGTH="6",
        HASHIDS_SALT="music for chameleons",
        # SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    hashids = Hashids(app)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route("/hello")
    def hello():
        return "Hello, World!"

    from . import db

    db.init_app(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import index

    app.register_blueprint(index.bp)

    from . import club

    app.register_blueprint(club.bp)

    from . import round

    app.register_blueprint(round.bp)

    app.add_url_rule("/", endpoint="index")

    return app
