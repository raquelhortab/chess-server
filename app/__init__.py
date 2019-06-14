import eventlet

eventlet.monkey_patch()

import redis as redis_srv
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO
from werkzeug.routing import BaseConverter

from app.game import GameNamespace
from config import config

bootstrap = Bootstrap()
redis = None


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def create_app(config_name):
    app = Flask(__name__, static_folder='../static')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)

    socketio = SocketIO(app, message_queue="redis://")

    global redis
    redis = redis_srv.from_url(app.config['REDIS_URL'])

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    app.url_map.converters['regex'] = RegexConverter

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # TODO: check this
    socketio.on_namespace(GameNamespace(redis, '/game'))

    return app, socketio
