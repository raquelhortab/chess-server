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

    def on_set_player_name(self, data):
        current_app.logger.error("set_player_name")
        if not data["game_id"] or not data["pc_id"] or not data["name"]:
            return 404
        if self.redis.exists(data["game_id"]):
            chess_game = self.load_game(data["game_id"])
            color = ""
            if str(chess_game.headers["White"]) == str(data["pc_id"]):
                color = "White"
            if str(chess_game.headers["Black"]) == str(data["pc_id"]):
                color = "Black"
            emit("inform_player_name", {"color":  color, "name": data["name"]}, room=data["game_id"])

    def on_refresh_board(self, data):
        if not data["game_id"]:
            return 404
        if self.redis.exists(data["game_id"]):
            chess_game = self.load_game(data["game_id"])
            current_app.logger.error(str(chess_game))
            # build board from game
            board = chess_game.board()
            for move in chess_game.mainline_moves():
                board.push(move)
            turn = "White" if board.turn else "Black"
            emit("refresh_board", {"fen": board.fen(), "turn": turn}, room=data["game_id"])

    def on_make_move(self, data):
        current_app.logger.error("on_make_move")
        current_app.logger.error(data["source"] + data["target"])
        if not data["target"] or not data["source"] or not data["game_id"]:
            return 404
        if self.redis.exists(data["game_id"]):
            chess_game = self.load_game(data["game_id"])
            current_app.logger.error(str(chess_game))
            new_move = chess.Move.from_uci(data["source"] + data["target"])
            # build board from game
            board = chess_game.board()
            for move in chess_game.mainline_moves():
                board.push(move)
            # check if move is legal
            if new_move in board.legal_moves:
                current_app.logger.error("LEGAL MOVE")
                board.push(new_move)
                new_game = chess.pgn.Game.from_board(board)
                new_game.headers = chess_game.headers
                self.redis.set(data["game_id"], str(new_game))
                current_app.logger.error("NEW GAME OBJECT:" + str(new_game))
                current_app.logger.error("NEW FEN:" + str(board.fen()))
                turn = "White" if board.turn else "Black"
                emit("move_resolution", {"fen": board.fen(), "legal_move": True, "turn": turn}, room=data["game_id"])
                if board.is_checkmate() or board.is_stalemate() or board.can_claim_draw():
                    if board.result() == "1-0":
                        winner = chess_game.headers["White"]
                    if board.result() == "0-1":
                        winner = chess_game.headers["Black"]
                    else:
                        winner = None
                    emit("game_finished", {"fen": board.fen(), "pgn": str(new_game), "winner": winner}, room=data["game_id"])
            else:
                current_app.logger.error("ILLEGAL MOVE")
                turn = "White" if board.turn else "Black"
                emit("move_resolution", {"fen": board.fen(), "legal_move": False, "turn": turn}, room=data["game_id"])

    #socket.emit("load_example_game",{game_id:game_id})
    def on_load_example_game(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = self.load_game(data["game_id"])
            if data["example"] == 1:
                board = chess.Board("8/8/8/1q6/8/2k5/8/K7 b - -")
            if data["example"] == 2:
                board = chess.Board("8/5K1k/8/8/p7/P1B5/8/8 w - - 33 124")
            new_game = chess.pgn.Game.from_board(board)
            new_game.headers["White"] = chess_game.headers["White"]
            new_game.headers["Black"] = chess_game.headers["Black"]
            new_game.headers["Event"] = chess_game.headers["Event"]
            self.redis.set(data["game_id"], str(new_game))
            turn = "White" if board.turn else "Black"
            emit("refresh_board", {"fen": board.fen(), "turn": turn}, room=data["game_id"])
