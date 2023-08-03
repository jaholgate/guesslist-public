import os

from flask import Flask
from flask_hashids import HashidMixin, Hashids
from flask_mail import Mail

hashids = Hashids()
mail = Mail()


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping()

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    hashids.init_app(app)
    mail.init_app(app)

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
