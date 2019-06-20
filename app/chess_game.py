import json
import chess
import re
from flask import current_app

class ChessGame:

    def __init__(self):
        self.pgn = '[White ""]\n[Black ""]\n[Event " "]\n'
        self.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

    def __str__(self):
        return "CHESS GAME: " + json.dumps(self.to_json())

    def load(self, chess_game_data):
        if chess_game_data != None:
            current_app.logger.error("before: " + str(chess_game_data))
            current_app.logger.error("after: " + str(chess_game_data.decode("utf-8")))
            tmp = json.loads(chess_game_data.decode("utf-8"))
            self.pgn = tmp["pgn"]
            self.fen = tmp["fen"]

    def to_json(self):
        return {"pgn": self.pgn, "fen": self.fen}

    def get_player_id(self, color):
        if not color:
            return None
        if color == "w":
            regex = r'\[\s*White\s*"(.*?)"\s*\]'
            matches = re.search(regex, self.pgn, re.I)
            return matches.group(1) if matches else None
        if color == "b":
            regex = r'\[\s*Black\s*"(.*?)"\s*\]'
            matches = re.search(regex, self.pgn, re.I)
            return matches.group(1) if matches else None
        return None

    def set_player_id(self, color, player_id):
        if not player_id:
            return False
        if color == "w":
            new = str("[White \"{}\"]").format(str(player_id))
            regex = r'\[\s*White\s*"(.*?)"\s*\]'
            self.pgn = re.sub(regex, new, self.pgn, re.I)
            return True
        if color == "b":
            new = str("[Black \"{}\"]").format(str(player_id))
            regex = r'\[\s*Black\s*"(.*?)"\s*\]'
            self.pgn = re.sub(regex, new, self.pgn, re.I)
            return True
        return False

    def get_player_color(self, player_id):
        if not player_id:
            return None
        if str(self.get_player_id("w")) == str(player_id):
            return "w"
        if str(self.get_player_id("b")) == str(player_id):
            return "b"
        return None

    def set_event(self, game_id):
        if not game_id:
            return False
        new = str("[Event \"{}\"]").format(str(game_id))
        regex = r'\[\s*Event\s*"(.*?)"\s*\]'
        self.pgn = re.sub(regex, new, self.pgn, re.I)
        return True


