import json
import re
import random
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

messaging = Blueprint('messaging', __name__)

class GameNamespace(Namespace):
    def __init__(self, redis, namespace=None):
        super(GameNamespace, self).__init__(namespace)
        self.redis = redis

    def on_connect(self):
        game_id = re.match(r'^.*/([A-Za-z0-9]{6}).*$', request.referrer).group(1)
        join_room(game_id)

    def on_spawn_beeper(self, data):
        if random.randint(1, 4) == 2: # accept 25% of requests
            bomb = None
            current_app.logger.error(data["game_id"] + ' spawn')
            with RedLock("redlock:{}".format(data["game_id"])):
                map = ImpactMap()
                map_data = self.redis.get(data["game_id"])
                map.load(map_data)
                beeper = map.spawn_beeper()
                if random.randint(1, 10) == 2: # accept 2.5% of requests
                  current_app.logger.error(data["game_id"] + ' spawnbomb')
                  bomb = map.spawn_bomb()

                # black karel
                black = map.spawn_black_karel()
                if black:
                    facing = {0: 'EAST', 1: 'WEST', 2: 'NORTH', 3: 'SOUTH'}[random.randint(0,3)]
                    msg = {"handle": "karel-black", "command": "spawn",
                           "params": {"x": black["x"], "y": black["y"], "facing": facing}}
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
                    map.kill_black_karel()
                    emit("command", json.dumps({"handle": "karel-black", "command": "die"}), room=data["game_id"])
                    map.from_compiler(karel_model.dump_world())


                self.redis.set(data["game_id"], json.dumps(map.impact_map))
            msg = {"handle": "common", "command": "spawnBeeper",
                   "params": {"x": beeper["x"], "y": beeper["y"]}}
            emit("command", json.dumps(msg), room=data["game_id"])
            if bomb:
              msg = {"handle": "common", "command": "spawnBomb",
                     "params": {"x": bomb["x"], "y": bomb["y"]}}
              emit("command", json.dumps(msg), room=data["game_id"])


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

                    karel_model.respawn(data["handle"])
                    msg = '{"handle": "%s", "command": "die"}' % (data["handle"])
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
