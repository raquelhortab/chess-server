import io
import re
import chess
import chess.pgn
from flask import Blueprint
from flask import current_app
from flask import request
from flask_socketio import Namespace, emit, join_room


messaging = Blueprint('messaging', __name__)


class GameNamespace(Namespace):

    def __init__(self, redis, namespace=None):
        super(GameNamespace, self).__init__(namespace)
        self.redis = redis

    def load_game(self, game_id):
        game_data = self.redis.get(game_id)
        stringIO = io.StringIO(game_data.decode("utf-8"))
        chess_game = chess.pgn.read_game(stringIO)
        return chess_game

    def on_connect(self):
        game_id = re.match(r'^.*/([A-Za-z0-9]{6}).*$', request.referrer).group(1)
        join_room(game_id)
        current_app.logger.error("on connect")

    def on_make_move(self, data):
        current_app.logger.error("on_make_move")
        current_app.logger.error(data["source"] + data["target"])
        if not data["target"] or not data["source"] or not data["game_id"]:
            return 404
        if self.redis.exists(data["game_id"]):
            chess_game = self.load_game(data["game_id"])
            current_app.logger.error(str(chess_game))
            new_move = chess.Move.from_uci(data["source"] + data["target"])
            board = chess_game.board()
            for move in chess_game.mainline_moves():
                board.push(move)
            current_app.logger.error(str(board.fen()))
            current_app.logger.error(str(board.legal_moves))
            if new_move in board.legal_moves:
                current_app.logger.error("LEGAL")
                board.push(new_move)
                current_app.logger.error(str(chess_game.variations))
                new_game = chess.pgn.Game.from_board(board)
                new_game.headers = chess_game.headers
                self.redis.set(data["game_id"], str(new_game))
                current_app.logger.error(str(new_game))
                emit("move_resolution", {"fen": board.fen(), "legal_move": True}, room=data["game_id"])
                if board.is_checkmate():
                    if board.result() == "1-0":
                        winner = chess_game.headers["White"]
                    if board.result() == "0-1":
                        winner = chess_game.headers["Black"]
                    emit("game_finished", {"fen": board.fen(), "winner": winner}, room=data["game_id"])
            else:
                current_app.logger.error("ILLEGAL")
                emit("move_resolution", {"fen": board.fen(), "legal_move": False}, room=data["game_id"])

    def on_load_example_game(self, data):
        if self.redis.exists(data["game_id"]):
            board = chess.Board("8/8/8/1q6/8/2k5/8/K7 b - -")
            chess_game = chess.pgn.Game.from_board(board)
            self.redis.set(data["game_id"], str(chess_game))
            emit("move_resolution", {"fen": board.fen(), "legal_move": True}, room=data["game_id"])
