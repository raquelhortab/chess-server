import json
import os
import ast

from flask import current_app
from flask import flash
from flask import render_template, send_from_directory
from flask import request, jsonify
import datetime
from werkzeug.utils import redirect

from app import game, redis
from app.impact_map import ImpactMap
from app.chess_game import ChessGame
from app.main.forms import GameForm
from . import main


@main.route("/<regex('([A-Za-z0-9]{6})'):game_id>", methods=["GET", "POST"])
def chessboard(game_id):
    current_app.logger.error("chessboard, game_id: " + str(game_id))
    pc_id = request.args.get('pc_id')
    chess_game = ChessGame()
    # Existing game
    if redis.exists(game_id):
        current_app.logger.error("   Existing game")
        chess_game.load(redis.get(game_id))
        # if new player
        if not chess_game.get_player_color(pc_id):
            current_app.logger.error("       New player")
            # if empty seat
            if not chess_game.get_player_id("b"):
                chess_game.set_player_id("b", pc_id)
            # if game full
            else:
                return "404"
        color = chess_game.get_player_color(pc_id)
        current_app.logger.error(str("   Player {} is color {}").format(str(pc_id),str(color)))
    # New game
    else:
        current_app.logger.error("   New game")
        chess_game.set_player_id("w", pc_id)
        chess_game.set_event(game_id)
        color = "w"
        current_app.logger.error(str("   Player {} is color {}").format(str(pc_id),str(color)))
    redis.set(game_id, json.dumps(chess_game.to_json()))
    current_app.logger.error("CHESSBOARD VIEW: " + str(chess_game))
    current_app.logger.error("type: " + str(type(chess_game.get_player_id("w"))) + str(type(chess_game.get_player_id("b"))))
    return render_template('chessboard.html', color=color, white=chess_game.get_player_id("w"), black=chess_game.get_player_id("b"), game_id=game_id, pgn=chess_game.pgn)

#
# @main.route("/<regex('([A-Za-z0-9]{6})'):game_id>/create",methods=['GET', 'POST'])
# def create_game(game_id):
#     current_app.logger.error("create_game")
#     current_app.logger.error(str(request.args))
#     chess_game = ChessGame()
#     white = request.args.get('white')
#     black = request.args.get('black')
#     if redis.exists(game_id):
#         chess_game.load(redis.get(game_id))
#         chess_game.color_mapping["w"] = white if white else ""
#         chess_game.color_mapping["b"] = black if black else ""
#         result = {"existed": True, "pgn": chess_game.pgn, "fen": chess_game.fen}
#         current_app.logger.error("I got here 1")
#         current_app.logger.error(datetime.datetime.now())
#         return jsonify(
#             summary= "aaa"
#         )
#         return "ok"
#         return current_app.response_class(result, content_type='application/json')
#     else:
#         chess_game.pgn = request.args.get('pgn')
#         chess_game.fen = request.args.get('fen')
#         chess_game.color_mapping["w"] = white if white else ""
#         chess_game.color_mapping["b"] = black if black else ""
#         redis.set(game_id, json.dumps(chess_game.to_json()))
#         result = {"existed": False}
#         current_app.logger.error("I got here 2")
#         current_app.logger.error(datetime.datetime.now())
#         return jsonify(
#             summary="aaa"
#         )
#         return "ok"
#         return current_app.response_class(result, content_type='application/json')
#


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

