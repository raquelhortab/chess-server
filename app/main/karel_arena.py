import json
import os
import ast

from flask import current_app
from flask import flash
from flask import render_template, send_from_directory
from flask import request
from werkzeug.utils import redirect

from app import game, redis
from app.impact_map import ImpactMap
from app.main.forms import GameForm
from . import main


@main.route("/<regex('([A-Za-z0-9]{6})'):game_id>", methods=["GET", "POST"])
def chessboard(game_id):
    current_app.logger.error("chessboard, game_id: " + str(game_id))
    color = request.args.get('color')
    project_id = request.args.get('project_id')
    white = request.args.get('white')
    black = request.args.get('black')
    if not redis.exists(game_id):
        redis.set(game_id, None)
    return render_template('chessboard.html', color=color, project_id=project_id, white=white, black=black, game_id=game_id)



def run_game(game_id):
    current_app.logger.error("karel_arena.run_game")
    tv_mode = request.args.get('mode') == "tv"
    key_pl = "{}|players".format(game_id)
    players = redis.hgetall(key_pl)
    nickname = request.args.get('nickname')
    pc_id = request.args.get('pc_id')
    allow_conf = bool(int(request.args.get('allow_conf')))
    if len(players) >= 4 and not(pc_id in players) and not(tv_mode):
        flash("This game is full, start a new one", "errors")
        return render_template('index.html')

    current_app.logger.error(players)

    if not redis.exists(game_id):
        impact_map = ImpactMap()
        impact_map.initialize(request.args.get('level'))
        redis.set(game_id, json.dumps(impact_map.impact_map))

    form = GameForm()
    if form.validate_on_submit():
        pc_id = form.data['pc_id']

    if tv_mode:
        return render_template(
            'game.html',
            game_id=game_id,
            pc_id=pc_id,
            handle='tv',
            players=players
        )

    if len(players) > 0 and pc_id in players:

        return render_template(
            'game.html',
            game_id=game_id,
            pc_id=pc_id,
            handle=json.loads(players[str(pc_id)])['h'],
            players=players
        )
    else:
        return render_template('setup.html', game_id=game_id, form=form, nickname=nickname, pc_id=pc_id, players=players, allow_conf=allow_conf)



@main.route("/<regex('([A-Za-z0-9]{6})'):game_id>/reset")
def reset_game(game_id):
    redis.delete(game_id)
    return "OK"


@main.route("/<regex('([A-Za-z0-9]{6})'):game_id>/map")
def send_map(game_id):
    impact_map = ImpactMap()
    impact_map.load(redis.get(game_id))
    return str(impact_map)


@main.route('/')
def index():
    flash("Game not found", "errors")
    return render_template('index.html')

