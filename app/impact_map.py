import json
import random
import re
from flask import current_app


START = """LevelLevel0=/*JSON[*/"""
END = """/*]JSON*/;
LevelLevel0Resources=[new ig.Image('media/tileset.png')];
"""


def to_map(coord):
    return int(coord / 24)


def from_map(coord):
    return coord * 24


class ImpactMap:
    def __init__(self):
        self.impact_map = {}

    def initialize(self, level_name):
        with open('levels/' + level_name + '.json') as f:
            self.impact_map = json.loads(f.read())
        self.karel_initial_positions = self.get_initial_positions()

    def load(self, map):
        self.impact_map = json.loads(map.decode("utf-8"))

    def __str__(self):
        return START + json.dumps(self.impact_map) + END

    def get_dimension(self):
        return self.impact_map["layer"][0]["width"], self.impact_map["layer"][0]["height"]

    def _get_collision_layer(self):
        for layer in self.impact_map["layer"]:
            if layer["name"] == "collision":
                return layer

    def _get_bg_layer(self):
        for layer in self.impact_map["layer"]:
            if layer["name"] != "collision":
                return layer

    def get_walls(self):
        bg_layer = self._get_bg_layer()
        rows, cols = self.get_dimension()
        walls = []
        for i in range(0, cols):
            for j in reversed(range(0, rows)):
                if bg_layer["data"][i][j] == 4:
                    walls.append((i, j))
        return walls

    def get_stones(self):
        bg_layer = self._get_bg_layer()
        rows, cols = self.get_dimension()
        stones = []
        for i in range(0, cols):
            for j in reversed(range(0, rows)):
                if bg_layer["data"][i][j] == 3:
                    stones.append((i, j))
        return stones

    def get_beepers(self):
        beepers = []
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityBeeper":
                beepers.append((to_map(entity["y"]), to_map(entity["x"])))
        return beepers

    def get_bombs(self):
        bombs = []
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityBomb":
                bombs.append((to_map(entity["y"]), to_map(entity["x"])))
        return bombs

    def allows_bombs(self):
        return "allows_bombs" in self.impact_map and self.impact_map["allows_bombs"]

    def allows_black_karel(self):
        #return True
        return "allows_black_karel" in self.impact_map and self.impact_map["allows_black_karel"]

    def _valid_place(self, x, y):
        collision_layer = self._get_collision_layer()
        if collision_layer["data"][y][x] == 1:
            return False
        mx = from_map(x)
        my = from_map(y)
        for entity in self.impact_map["entities"]:
            if entity["type"] in ["EntityKarel", "EntityTray"]: # EntityBeeper not here to prevent eventual infinite loops!
                if entity["x"] == mx and entity["y"] == my:
                    return False
        return True

    def _pick_random_position(self):
        rows, cols = self.get_dimension()
        x = y = None
        while True:
            x, y = random.randint(0, cols-1), random.randint(0, rows-1)
            if self._valid_place(x, y):
                break
        return x, y

    def spawn_beeper(self):
        x, y = self._pick_random_position()
        beeper = {
            "type": "EntityBeeper",
            "x": from_map(x),
            "y": from_map(y),
        }
        self.impact_map["entities"].append(beeper)
        return beeper

    def spawn_bomb(self):
        if self.allows_bombs():
          x, y = self._pick_random_position()
          bomb = {
              "type": "EntityBomb",
              "x": from_map(x),
              "y": from_map(y),
          }
          self.impact_map["entities"].append(bomb)
          return bomb

    def spawn_black_karel(self):
        if self.allows_black_karel():
          x, y = self._pick_random_position()
          facing = {0: 'EAST', 1: 'WEST', 2: 'NORTH', 3: 'SOUTH'}[random.randint(0,3)]
          black = {
              "type": "EntityKarel",
              "x": from_map(x),
              "y": from_map(y),
              "settings": {
                  "facing": facing,
                  "name": "karel-black"
              }
          }
          self.impact_map["entities"].append(black)
          return black

    def kill_black_karel(self):
        for entity in self.impact_map["entities"]:
          if entity["type"] == "EntityKarel" and entity["settings"]["name"] == 'karel-black':
            self.impact_map["entities"].remove(entity)


    def get_initial_positions(self):
        karels = {}
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityKarel":
                handle = entity["settings"]["name"]
                karels[handle] = [entity["y"], entity["x"], entity["settings"]["facing"]]
        return karels

    def reset_karel(self, handle):
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityKarel":
                entity_name = entity["settings"]["name"]
                if entity_name == handle:
                    entity["y"] = self.karel_initial_positions[handle][0]
                    entity["x"] = self.karel_initial_positions[handle][1]
                    entity["settings"]["facing"] = self.karel_initial_positions[handle][2]

    def get_karels(self):
        karels = []
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityKarel":
                karels.append((entity["settings"]["name"], to_map(entity["y"]), to_map(entity["x"]), entity["settings"]["facing"]))
        return karels

    def get_trays(self):
        trays = []
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityTray":
                trays.append(
                    (
                        to_map(entity["y"]),
                        to_map(entity["x"]),
                        entity["settings"]["capacity"],
                        entity["settings"]["required"],
                        entity["settings"]["initialBeepers"],
                        entity["settings"]["owner"],
                    )
                )
        return trays

    def get_exits(self):
        exits = []
        for entity in self.impact_map["entities"]:
            if entity["type"] == "EntityExit":
                exits.append(
                    (
                        to_map(entity["y"]),
                        to_map(entity["x"]),
                    )
                )
        return exits

    def to_compiler(self):
        world = {}
        world["dimension"] = self.get_dimension()
        world["walls"] = self.get_walls()
        world["stones"] = self.get_stones()
        world["beepers"] = self.get_beepers()
        world["karels"] = self.get_karels()
        world["trays"] = self.get_trays()
        world["exits"] = self.get_exits()
        world["bombs"] = self.get_bombs()
        return world

    def from_compiler(self, world):
        entities_to_clear = ["EntityBeeper", "EntityKarel", "EntityTray", "EntityBomb"]
        entities = [e for e in self.impact_map["entities"] if e["type"] not in entities_to_clear]

        for y, x in world["beepers"]:
            beeper = {
                "type": "EntityBeeper",
                "x": from_map(x),
                "y": from_map(y)
            }
            entities.append(beeper)
        for y, x in world["bombs"]:
            bomb = {
                "type": "EntityBomb",
                "x": from_map(x),
                "y": from_map(y)
            }
            entities.append(bomb)
        for y, x, capacity, required, num_beepers, owner in world["trays"]:
            tray = {
                "type": "EntityTray",
                "x": from_map(x),
                "y": from_map(y),
                "settings": {
                    "capacity": capacity,
                    "initialBeepers": num_beepers,
                    "required": required,
                    "owner": owner
                }
            }
            entities.append(tray)
        for name, y, x, dir in world["karels"]: # :S
            if name == 'karel-black':
              continue
            karel = {
                "type": "EntityKarel",
                "x": from_map(x),
                "y": from_map(y),
                "settings": {
                    "facing": dir,
                    "name": name
                }
            }
            entities.append(karel)

        self.impact_map["entities"] = entities

        rows, cols = self.get_dimension()
        collision_layer = self._get_collision_layer()
        bg_layer = self._get_bg_layer()
        for i in range(0, cols):
            for j in reversed(range(0, rows)):
                collision_layer["data"][i][j] = 0
                if bg_layer["data"][i][j] == 4:
                  bg_layer["data"][i][j] = 2 # put all walls as floor
        for x,y in world["walls"]:
            collision_layer['data'][x][y] = 1
            bg_layer["data"][x][y] = 4
        for x,y in world["stones"]:
            collision_layer['data'][x][y] = 1
            bg_layer["data"][x][y] = 3

if __name__ == '__main__':
    m = Map()
    print(m)
