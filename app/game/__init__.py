import json
import re
import random
import chess
from functools import partial

import socketIO_client
from flask import Blueprint
from flask import current_app
from flask import request
from flask_socketio import Namespace, emit, join_room
from pykarel.karel_compiler import KarelCompiler
from redlock import RedLock

from app.impact_map import ImpactMap
from app.karel import DyingException, Karel
from app.karel_model import KarelModel
from app.chess_game import ChessGame

messaging = Blueprint('messaging', __name__)


class GameNamespace(Namespace):

    def __init__(self, redis, namespace=None):
        super(GameNamespace, self).__init__(namespace)
        self.redis = redis

    def on_connect(self):
        game_id = re.match(r'^.*/([A-Za-z0-9]{6}).*$', request.referrer).group(1)
        join_room(game_id)
        current_app.logger.error("on connect")

    def on_make_move(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = ChessGame()
            chess_game.load(self.redis.get(data["game_id"]))
            current_app.logger.error("on_make_move: from " + str(data["source"]) + " to " + str(data["target"]))
            current_app.logger.error("fen: " + chess_game.fen)
            current_app.logger.error("new pgn: " + str(data["pgn"]))
            board = chess.Board(chess_game.fen)
            move = chess.Move.from_uci(data["source"] + data["target"])
            current_app.logger.error("chess.Move: " + str(move))
            current_app.logger.error("legal moves: " + str(board.legal_moves))
            if move in board.legal_moves:
                chess_game.pgn = data["pgn"]
                chess_game.fen = data["fen"]
                current_app.logger.error(chess_game.pgn)
                self.redis.set(data["game_id"], json.dumps(chess_game.to_json()))
                emit("move_resolution", {"pgn": chess_game.pgn, "legal_move": True}, room=data["game_id"])
                # check finished
                board = chess.Board(chess_game.fen)
                winner = None
                if board.is_checkmate():
                    if board.result() == "1-0":
                        winner = chess_game.get_player_id("w")
                    if board.result() == "0-1":
                        winner = chess_game.get_player_id("b")
                    emit("game_finished", {"pgn": chess_game.pgn, "winner": winner}, room=data["game_id"])
            else:
                current_app.logger.error(chess_game.pgn)
                emit("move_resolution", {"pgn": chess_game.pgn, "legal_move": False}, room=data["game_id"])

    def on_get_pgn(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = ChessGame()
            chess_game.load(self.redis.get(data["game_id"]))
            emit("updated_pgn", {"pgn": chess_game.pgn}, room=data["game_id"])
            current_app.logger.error("on_get_pgn: " + str(chess_game))

    def on_finish_game(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = ChessGame()
            chess_game.load(self.redis.get(data["game_id"]))
            board = chess.Board(chess_game.fen)
            winner = None
            if board.is_checkmate():
                if board.result() == "1-0":
                    winner = chess_game.get_player_id("w")
                if board.result() == "0-1":
                    winner = chess_game.get_player_id("b")
                emit("game_finished", {"pgn": chess_game.pgn, "winner": winner}, room=data["game_id"])

    def on_load_example_game(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = ChessGame()
            chess_game.pgn = data["pgn"]
            chess_game.fen = data["fen"]
            self.redis.set(data["game_id"], json.dumps(chess_game.to_json()))
            emit("updated_pgn", {"pgn": chess_game.pgn}, room=data["game_id"])
            current_app.logger.error("on_load_example_game: " + str(chess_game))
