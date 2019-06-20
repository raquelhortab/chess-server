import json
import os
import ast
import chess
import chess.pgn
import io

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
    current_app.logger.error("chessboard, game_ida: " + str(game_id))
    pc_id = request.args.get('pc_id')
    if not pc_id:
        return "No pc"
    # Existing game
    if redis.exists(game_id):
        current_app.logger.error("   Existing game")
        chess_game = load_game(game_id)
        current_app.logger.error(str(chess_game))
        # if new player
        if not get_player_color(chess_game, pc_id):
            current_app.logger.error("       New player")
            # if empty seat
            if chess_game.headers["Black"] == "?":
                chess_game.headers["Black"] = str(pc_id)
            # if game full
            else:
                return "Game full"
        color = get_player_color(chess_game,pc_id)
        current_app.logger.error(str("   Player {} is color {}").format(str(pc_id), str(color)))
    # New game
    else:
        chess_game = chess.pgn.Game()
        current_app.logger.error("   New game")
        chess_game.headers["White"] = str(pc_id)
        chess_game.headers["Event"] = str(game_id)
        color = "w"
        current_app.logger.error(str("   Player {} is color {}").format(str(pc_id), str(color)))
    redis.set(game_id, str(chess_game))
    board = chess_game.board()
    for move in chess_game.mainline_moves():
        board.push(move)
    current_app.logger.error(str(board.fen()))
    return render_template('chessboard.html', color=color, white=chess_game.headers["White"], black=chess_game.headers["Black"], game_id=game_id, pgn=str(chess_game), fen=str(board.fen()))

def load_game(game_id):
    game_data = redis.get(game_id)
    stringIO = io.StringIO(game_data.decode("utf-8"))
    chess_game = chess.pgn.read_game(stringIO)
    return chess_game

def get_player_color(game, player_id):
    if not player_id:
        return None
    if str(game.headers["White"]) == str(player_id):
        return "w"
    if str(game.headers["Black"]) == str(player_id):
        return "b"
    return None

# def old_chessboard(game_id):
#     current_app.logger.error("chessboard, game_id: " + str(game_id))
#     pc_id = request.args.get('pc_id')
#     chess_game = ChessGame()
#     # Existing game
#     if redis.exists(game_id):
#         current_app.logger.error("   Existing game")
#         chess_game.load(redis.get(game_id))
#         # if new player
#         if not chess_game.get_player_color(pc_id):
#             current_app.logger.error("       New player")
#             # if empty seat
#             if not chess_game.get_player_id("b"):
#                 chess_game.set_player_id("b", pc_id)
#             # if game full
#             else:
#                 return "404"
#         color = chess_game.get_player_color(pc_id)
#         current_app.logger.error(str("   Player {} is color {}").format(str(pc_id),str(color)))
#     # New game
#     else:
#         current_app.logger.error("   New game")
#         chess_game.set_player_id("w", pc_id)
#         chess_game.set_event(game_id)
#         color = "w"
#         current_app.logger.error(str("   Player {} is color {}").format(str(pc_id),str(color)))
#     redis.set(game_id, json.dumps(chess_game.to_json()))
#     current_app.logger.error("CHESSBOARD VIEW: " + str(chess_game))
#     current_app.logger.error("type: " + str(type(chess_game.get_player_id("w"))) + str(type(chess_game.get_player_id("b"))))
#     return render_template('chessboard.html', color=color, white=chess_game.get_player_id("w"), black=chess_game.get_player_id("b"), game_id=game_id, pgn=chess_game.pgn)
#
