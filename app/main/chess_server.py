import chess
import chess.pgn
import io

from flask import current_app
from flask import render_template
from flask import request

from app import redis
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
        color = "White"
        current_app.logger.error(str("   Player {} is color {}").format(str(pc_id), str(color)))
    redis.set(game_id, str(chess_game))
    board = chess_game.board()
    for move in chess_game.mainline_moves():
        board.push(move)
    current_app.logger.error(str(board.fen()))
    turn = "White" if board.turn else "Black"
    if board.is_checkmate() or board.is_stalemate():
        if board.result() == "1-0":
            winner = chess_game.headers["White"]
        if board.result() == "0-1":
            winner = chess_game.headers["Black"]
        else:
            winner = ""
        return render_template('chessboard.html', color=color, white=chess_game.headers["White"],black=chess_game.headers["Black"], game_id=game_id, pgn=str(chess_game),fen=str(board.fen()), turn=turn, game_over=True, winner=winner)
    else:
        return render_template('chessboard.html', color=color, white=chess_game.headers["White"], black=chess_game.headers["Black"], game_id=game_id, pgn=str(chess_game), fen=str(board.fen()), turn=turn, game_over=False, winner=None)


def load_game(game_id):
    game_data = redis.get(game_id)
    stringIO = io.StringIO(game_data.decode("utf-8"))
    chess_game = chess.pgn.read_game(stringIO)
    return chess_game


def get_player_color(game, player_id):
    if not player_id:
        return None
    if str(game.headers["White"]) == str(player_id):
        return "White"
    if str(game.headers["Black"]) == str(player_id):
        return "Black"
    return None
