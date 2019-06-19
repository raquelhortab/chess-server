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
            else:
                current_app.logger.error(chess_game.pgn)
                emit("move_resolution", {"pgn": chess_game.pgn, "legal_move": False}, room=data["game_id"])

        # def on_update_pgn(self, data):
        #     chess_game = ChessGame()
        #     chess_game.load(self.redis.get(data["game_id"]))
        #     chess_game.pgn = data["pgn"]
        #     self.redis.set(data["game_id"], json.dumps(chess_game.to_json()))
        #     current_app.logger.error("on_update_pgn" + str(chess_game))
        #
        # def on_get_pgn(self, data):
        #     chess_game = ChessGame()
        #     chess_game.load(self.redis.get(data["game_id"]))
        #     emit("updated_pgn", chess_game.pgn, room=data["game_id"])
        #     current_app.logger.error("on_get_pgn: " + str(chess_game))
        #
        # def on_connect(self):
        #     game_id = re.match(r'^.*/([A-Za-z0-9]{6}).*$', request.referrer).group(1)
        #     join_room(game_id)
        #     current_app.logger.error("on connect")

    # def on_update_pgn(self, data):
    #     current_app.logger.error("on_update_pgn")
    #     chess_game = ChessGame()
    #     if self.redis.exists(data["game_id"]):
    #         chess_game.load(self.redis.get(data["game_id"]))
    #     chess_game.pgn = data["pgn"]
    #     chess_game.fen = data["fen"]
    #     current_app.logger.error(str(chess_game))
    #     self.redis.set(data["game_id"], json.dumps(chess_game.to_json()))

    def on_get_pgn(self, data):
        if self.redis.exists(data["game_id"]):
            chess_game = ChessGame()
            chess_game.load(self.redis.get(data["game_id"]))
            emit("updated_pgn", {"pgn": chess_game.pgn}, room=data["game_id"])
            current_app.logger.error("on_get_pgn: " + str(chess_game))



    ##########################################################################################



    def on_spawn_beeper(self, data):
        if random.randint(1, 4) == 2: # accept 25% of requests
            bomb = None
            current_app.logger.error(data["game_id"] + ' spawn')
            with RedLock("redlock:{}".format(data["game_id"])):
                map = ImpactMap()
                map_data = self.redis.get(data["game_id"])
                map.load(map_data)
                beeper = map.spawn_beeper()
                current_app.logger.error(data["game_id"] + ' endspawn' + str(beeper["x"]) + str(beeper["y"]))
                msg = {"handle": "common", "command": "spawnBeeper",
                       "params": {"x": beeper["x"], "y": beeper["y"]}}
                emit("command", json.dumps(msg), room=data["game_id"])

                if random.randint(1, 10) == 2: # accept 2.5% of requests
                    current_app.logger.error(data["game_id"] + ' spawnbomb')
                    allow_bombs = self.redis.get("{}|allow_bombs".format(data["game_id"]))
                    if allow_bombs is not None and bool(int(allow_bombs)):
                        bomb = map.spawn_bomb()
                        if bomb is not None:
                          current_app.logger.error("spawnbomb done")
                          msg = {"handle": "common", "command": "spawnBomb",
                                 "params": {"x": bomb["x"], "y": bomb["y"]}}
                          emit("command", json.dumps(msg), room=data["game_id"])

                # black karel
                allow_black_karel = self.redis.get("{}|allow_black_karel".format(data["game_id"]))
                if allow_black_karel is not None and bool(int(allow_black_karel)) and random.randint(1, 2) == 1: # accept 12.5% of requests
                    black = map.spawn_black_karel()
                else:
                    black = None

                if black:
                    msg = {"handle": "karel-black", "command": "spawn",
                           "params": {"x": black["x"], "y": black["y"], "facing": black["settings"]["facing"]}}
                    emit("command", json.dumps(msg), room=data["game_id"])
                    karel_model = KarelModel(current_app.logger)
                    karel_model.load_world(map.to_compiler())

                    karel = Karel(karel_model, data["game_id"], None, "karel-black")
                    compiler = KarelCompiler(karel)
                    try:
                        compiler.compile(karel.black_code())
                    except Exception as e:
                        emit("error", (str(e), 'karel-black'), room=data["game_id"])
                    else:
                        try:
                            steps = 500 # random number to avoid endless loops
                            while not compiler.execute_step():
                                steps -= 1
                                if steps < 0:
                                  raise DyingException('Too many steps. Endless loop?')
                        except (DyingException, Exception) as e:
                            current_app.logger.error(e)
                            emit("error", (str(e), 'karel-black'), room=data["game_id"])
                    map.from_compiler(karel_model.dump_world())
                    map.kill_black_karel()
                    emit("command", json.dumps({"handle": "karel-black", "command": "die"}), room=data["game_id"])

                self.redis.set(data["game_id"], json.dumps(map.impact_map))


    def on_execute(self, data):
        current_app.logger.error(data["game_id"] + ' execute')
        karel_model = KarelModel(current_app.logger)
        with RedLock("redlock:{}".format(data["game_id"])):
            map = ImpactMap()
            map.load(self.redis.get(data["game_id"]))
            karel_model.load_world(map.to_compiler())
            karel = Karel(karel_model, data["game_id"], data["pc_id"], data["handle"])
            compiler = KarelCompiler(karel)

            try:
                compiler.compile(str(data["code"]))
            except Exception as e:
                emit("error", (str(e), data['handle']), room=data["game_id"])
            else:
                try:
                    steps = 500 # random number to avoid endless loops
                    while not compiler.execute_step():
                        steps -= 1
                        if steps < 0:
                          raise DyingException('Too many steps. Endless loop?')
                except (DyingException, Exception) as e:
                    emit("error", (str(e), data['handle']), room=data["game_id"])

                if True:  # After the code, any remaining beeper is returned and the map saved
                    for beeper in iter(partial(karel_model.return_beeper, data["handle"]), None):
                        msg = {"handle": data["handle"], "command": "spawnBeeper",
                               "params": {"x": beeper[1] * 24, "y": beeper[0] * 24}}
                        current_app.logger.error('undoemit')
                        emit("command", json.dumps(msg), room=data["game_id"])
                    map.update_initial_positions(karel_model)
                    karel_model.respawn(data["handle"])
                    msg = '{"handle": "%s", "command": "die"}' % (data["handle"])
                    current_app.logger.error("no more steps: die")
                    emit('command', msg, room=data["game_id"])
                    map.from_compiler(karel_model.dump_world())
                    self.redis.set(data["game_id"], json.dumps(map.impact_map))


    def on_pick_karel(self, data):
        current_app.logger.error("onpick")
        join_room(data["game_id"])
        key = "{game_id}|{pc_id}".format(**data)
        self.redis.set(key, (data["handle"], data["nickname"]))
        key_pl = "{game_id}|players".format(**data)
        players = self.redis.hgetall(key_pl)

        # Check that the handle is not already taken. If so, ignore the event
        for player_id, json_data in players.iteritems():
          stored_data = json.loads(json_data)
          if stored_data['h'] == data['handle'] and player_id != data['pc_id']:
            return

        jsoned_data = json.dumps({"h": data["handle"], "n": data["nickname"]})
        players[data['pc_id']] = jsoned_data
        self.redis.hmset(key_pl, players)
        current_app.logger.error(players)
        emit('pick_karel', (data["pc_id"], jsoned_data), room=data["game_id"])

    def on_allow_bombs_change(self, data):
        current_app.logger.error("on allow bombs")
        join_room(data["game_id"])
        key = "{}|allow_bombs".format(data["game_id"])
        self.redis.set(key, data["allow_bombs"])

    def on_allow_black_karel_change(self, data):
        current_app.logger.error("on allow black karel")
        join_room(data["game_id"])
        key = "{}|allow_black_karel".format(data["game_id"])
        self.redis.set(key, data["allow_black_karel"])
