import chess.pgn
from flask import current_app


class ChessGame(chess.pgn.Game):

    # def get_player_id(self, color):
    #     if not color:
    #         return None
    #     if color == "w" or color.lower() == "white":
    #         return self.headers["White"]
    #     if color == "b" or color.lower() == "black":
    #         return self.headers["black"]
    #
    # def set_player_id(self, color, player_id):
    #     if not player_id or not color:
    #         return False
    #     if color == "w" or color.lower() == "white":
    #         self.headers["White"] = str(player_id)
    #     if color == "b" or color.lower() == "black":
    #         self.headers["Black"] = str(player_id)
    #         return True
    #     return False

    def get_player_color(self, player_id):
        if not player_id:
            return None
        if str(self.headers["White"]) == str(player_id):
            return "w"
        if str(self.headers["Black"]) == str(player_id):
            return "b"
        return None

    # def set_event(self, game_id):
    #     if not game_id:
    #         return False
    #     self.headers["Event"] = str(game_id)
    #     return True
