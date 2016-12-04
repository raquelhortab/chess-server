from flask import render_template, send_from_directory

from app import game
from . import main


@main.route('/')
def hello():
    return render_template('index.html')


@main.route('/lib/<path:path>')
def send_lib(path):
    return send_from_directory('../static/lib', path)


@main.route('/media/<path:path>')
def send_media(path):
    return send_from_directory('../static/media', path)


@main.route('/map')
def send_map():
    return str(game.impact_map)