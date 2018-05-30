import copy

from pykarel.karel.beepers import Beepers
from pykarel.karel.exits import Exits
from pykarel.karel.karel_constants import KAREL_EAST, KAREL_WEST, KAREL_NORTH, KAREL_SOUTH
from pykarel.karel.trays import Trays, Tray
from pykarel.karel.walls import Walls
from flask import current_app


def error(txt):
    current_app.logger.error(txt)


class KarelEntity:
    def __init__(self, handle, row, col, dir):
        self.handle = handle
        self.row = row
        self.col = col
        self.dir = dir
        self.bag = []

    def __str__(self):
        return "Karel '{}' at {}, {} facing {} having {} beepers".format(self.handle, self.row, self.col, self.dir,
                                                                         len(self.bag))

class OwnedTray(Tray):
    def __init__(self, capacity, required, initial_beepers, owner):
        self.capacity = capacity
        self.required = required
        self.num_beepers = initial_beepers
        self.owner = owner

    def is_full(self):
        return self.capacity == self.num_beepers

class OwnedTrays(Trays):
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.trays = [[None for i in range(cols)] for j in range(rows)]
        self.trays_by_owner = {}

    def add_tray(self, row, col, capacity, required, initial_beepers, owner):
        new_tray = OwnedTray(capacity, required, initial_beepers, owner)
        self.trays[row][col] = new_tray
        if not owner in self.trays_by_owner:
          self.trays_by_owner[owner] = []
        self.trays_by_owner[owner].append(new_tray)

    def is_owner(self, row, col, owner):
        return owner == self.trays[row][col].owner

    def owner_trays_full(self, owner):
        return all(tray.is_full() for tray in self.trays_by_owner[owner])

    def dump(self):
        for i in range(self.cols):
            for j in range(self.rows):
                if self.trays[i][j] != None:
                    tray = self.trays[i][j]
                    yield i, j, tray.capacity, tray.required, tray.num_beepers, tray.owner

class RemovableWalls(Walls):
    def remove_wall(self, row, col):
        if col < 0 or col >= self.cols:
            return False
        if row < 0 or row >= self.rows:
            return False
        self.walls[row][col] = 0

class Bombs(RemovableWalls):
    def add_bomb(self, row, col):
        self.add_wall(row, col)

    def remove_bomb(self, row, col):
        ok = self.remove_wall(row, col)

    def is_bomb(self, row, col):
        return self.walls[row][col] == 1

class KarelModel:
    def __init__(self, logger):
        self.logger = logger
        self.beepers = None
        self.trays = None
        self.exits = None
        self.walls = None
        self.stones = None
        self.bombs = None
        self.karels = {}
        self.karels_initial = {}
        self.rows = 0
        self.cols = 0

    def exit(self, handle):
        if self.exits.exit_present(self.karels[handle].row, self.karels[handle].col) and \
          self.trays.owner_trays_full(handle):
            return True
        return False

    def create_wall(self, handle):
        row, col = self.__get_pos(handle)
        if not self.front_is_clear(handle):
            error("Front is not empty")
            return False
        else:
            new_row, new_col = self.__next_pos(handle)
            self.walls.add_wall(new_row, new_col)
            return True

    def remove_wall(self, handle):
        row, col = self.__get_pos(handle)
        if self.front_is_clear(handle):
            error("Front is clear")
            return False
        else:
            if self.is_removable_wall(handle):
                new_row, new_col = self.__next_pos(handle)
                self.walls.remove_wall(new_row, new_col)
                return True
            else:
                error("Stone wall")
                return False

    def explode_bomb(self, handle):
        new_row, new_col = self.__next_pos(handle)
        self.bombs.remove_bomb(new_row, new_col)
        return True

    def move(self, handle):
        new_row, new_col = self.__next_pos(handle)
        if self.front_is_clear(handle):
            self.karels[handle].row = new_row
            self.karels[handle].col = new_col
            return True
        else:
            self.logger.info("row: {} col: {} dir: {}".format(new_row, new_col, dir))
            error("Front is blocked")
        return False

    def turn_left(self, handle):
        new_d = self.karels[handle].dir
        if self.karels[handle].dir == KAREL_EAST:
            new_d = KAREL_NORTH
        elif self.karels[handle].dir == KAREL_WEST:
            new_d = KAREL_SOUTH
        elif self.karels[handle].dir == KAREL_NORTH:
            new_d = KAREL_WEST
        elif self.karels[handle].dir == KAREL_SOUTH:
            new_d = KAREL_EAST
        else:
            error("invalid dir: {}".format(self.dir))
        self.karels[handle].dir = new_d

    def turn_right(self, handle):
        new_d = self.karels[handle].dir
        if self.karels[handle].dir == KAREL_EAST:
            new_d = KAREL_SOUTH
        elif self.karels[handle].dir == KAREL_WEST:
            new_d = KAREL_NORTH
        elif self.karels[handle].dir == KAREL_NORTH:
            new_d = KAREL_EAST
        elif self.karels[handle].dir == KAREL_SOUTH:
            new_d = KAREL_WEST
        else:
            error("invalid dir: {}".format(self.dir))
        self.karels[handle].dir = new_d

    def __get_pos(self, handle):
        return self.karels[handle].row, self.karels[handle].col

    def pick_beeper(self, handle):
        row, col = self.__get_pos(handle)
        if self.beepers.beeper_present(row, col):
            self.beepers.pick_beeper(row, col)
            self.karels[handle].bag.append((row, col))
        else:
            error("No beepers present")
            return False
        return True

    def put_beeper(self, handle):
        row, col = self.__get_pos(handle)
        if len(self.karels[handle].bag) > 0:
            self.beepers.put_beeper(row, col)
            self.karels[handle].bag.pop()
            return True
        else:
            error("Not carrying any beeper")
            return False

    def put_beeper_in_tray(self, handle):
        row, col = self.__get_pos(handle)
        if self.trays.tray_present(row, col):
            if len(self.karels[handle].bag) > 0 and not self.trays.tray_is_full(row, col):
                self.trays.put_beeper(row, col)
                self.karels[handle].bag.pop()
                return True
            else:
                error("Not carrying any beeper or full tray")
                return False
        else:
            error("No trays present")
            return False

    def pick_beeper_from_tray(self, handle):
        '''
        row, col = self.__get_pos(handle)
        if self.trays.tray_present(row, col):
            self.trays.pick_beeper(row, col)
            self.karels[handle].bag.append((0, 0))
            return True
        else:
            error("No trays present")
            return False
        '''
        return False # disabled for now to prevent abuse

    def convert_beeper_into_bomb(self, handle):
        row, col = self.__get_pos(handle)
        if len(self.karels[handle].bag) > 0:
            self.bombs.add_bomb(row, col)
            self.karels[handle].bag.pop()
            return True
        else:
            error("Not carrying any beeper")
            return False

    def return_beeper(self, handle):
        if len(self.karels[handle].bag) > 0:
            beeper_pos = self.karels[handle].bag.pop()
            self.beepers.put_beeper(*beeper_pos)
            return beeper_pos
        return None

    def get_direction(self, handle):
        return self.karels[handle].dir

    def get_num_rows(self):
        return self.rows

    def get_num_cols(self):
        return self.cols

    def get_karel_row(self, handle):
        return self.karels[handle].row

    def get_karel_col(self, handle):
        return self.karels[handle].col

    def get_num_beepers(self, handle):
        return len(self.karels[handle].bag)

    def is_removable_wall(self, handle):
        new_row, new_col = self.__next_pos(handle)
        # only thing that returns false is a stone or limit
        if new_col < 0 or new_col >= self.stones.cols:
            return False
        if new_row < 0 or new_row >= self.stones.rows:
            return False
        return self.stones.walls[new_row][new_col] != 1

    def beepers_present(self, handle):
        return self.beepers.beeper_present(self.get_karel_row(handle), self.get_karel_col(handle))

    def tray_present(self, handle):
        return self.trays.tray_present(self.get_karel_row(handle), self.get_karel_col(handle))

    def tray_full(self, handle):
        return self.trays.tray_is_full(self.get_karel_row(handle), self.get_karel_col(handle))

    def tray_empty(self, handle):
        return self.trays.tray_is_empty(self.get_karel_row(handle), self.get_karel_col(handle))

    def tray_complete(self, handle):
        return self.trays.tray_is_complete(self.get_karel_row(handle), self.get_karel_col(handle))

    def tray_is_mine(self, handle):
        return self.trays.is_owner(self.get_karel_row(handle), self.get_karel_col(handle), handle)

    def exit_present(self, handle):
        return self.exits.exit_present(self.get_karel_row(handle), self.get_karel_col(handle))

    def facing_north(self, handle):
        return self.karels[handle].dir == KAREL_NORTH

    def facing_east(self, handle):
        return self.karels[handle].dir == KAREL_EAST

    def facing_south(self, handle):
        return self.karels[handle].dir == KAREL_SOUTH

    def facing_west(self, handle):
        return self.karels[handle].dir == KAREL_WEST

    def __next_pos(self, handle):
        new_row = self.karels[handle].row
        new_col = self.karels[handle].col
        if self.karels[handle].dir is KAREL_EAST:
            new_col += 1
        elif self.karels[handle].dir is KAREL_WEST:
            new_col -= 1
        elif self.karels[handle].dir is KAREL_NORTH:
            new_row -= 1
        elif self.karels[handle].dir is KAREL_SOUTH:
            new_row += 1
        else:
            error("invalid dir: {}".format(self.karels[handle].dir))
        return new_row, new_col


    def front_is_clear(self, handle):
        new_row, new_col = self.__next_pos(handle)
        wall_free = self.walls.is_move_valid(self.karels[handle].row, self.karels[handle].col, new_row, new_col)
        stone_free = self.stones.is_move_valid(self.karels[handle].row, self.karels[handle].col, new_row, new_col)
        ret = wall_free and stone_free
        return ret

    def front_is_bomb(self, handle):
        new_row, new_col = self.__next_pos(handle)
        return self.bombs.is_bomb(new_row, new_col)

    def load_world(self, world):
        self.rows = world["dimension"][0]
        self.cols = world["dimension"][1]

        self.beepers = Beepers(self.rows, self.cols)
        self.walls = RemovableWalls(self.rows, self.cols)
        self.stones = Walls(self.rows, self.cols)
        self.trays = OwnedTrays(self.rows, self.cols)
        self.exits = Exits(self.rows, self.cols)
        self.bombs = Bombs(self.rows, self.cols)

        for beeper in world["beepers"]:
            self.beepers.put_beeper(beeper[0], beeper[1])

        for wall in world["walls"]:
            self.walls.add_wall(wall[0], wall[1])

        for stone in world["stones"]:
            self.stones.add_wall(stone[0], stone[1])

        for tray in world["trays"]:
            self.trays.add_tray(tray[0], tray[1], tray[2], tray[3], tray[4], tray[5])

        for exit in world["exits"]:
            self.exits.add_exit(exit[0], exit[1])

        for bomb in world["bombs"]:
            self.bombs.add_bomb(bomb[0], bomb[1])

        karel_direction = dict((
            ("EAST", KAREL_EAST),
            ("WEST", KAREL_WEST),
            ("NORTH", KAREL_NORTH),
            ("SOUTH", KAREL_SOUTH),
        ))

        for karel in world["karels"]:
            self.karels[karel[0]] = KarelEntity(karel[0], karel[1], karel[2], karel_direction[karel[3]])
            self.karels_initial[karel[0]] = KarelEntity(karel[0], karel[1], karel[2], karel_direction[karel[3]])

    def dump_world(self):
        world = {}
        world["dimension"] = [self.rows, self.cols]
        world["beepers"] = []
        for beeper in self.beepers.dump():
            world["beepers"].append(beeper)
        world["bombs"] = []
        for bomb in self.bombs.dump():
            world["bombs"].append(bomb)
        world["walls"] = []
        for wall in self.walls.dump():
            world["walls"].append(wall)
        world["stones"] = []
        for stone in self.stones.dump():
            world["stones"].append(stone)
        world["karels"] = []
        karel_direction = dict((
            (KAREL_EAST, "EAST"),
            (KAREL_WEST, "WEST"),
            (KAREL_NORTH, "NORTH"),
            (KAREL_SOUTH, "SOUTH"),
        ))
        for karel in self.karels.values():
            world["karels"].append([karel.handle, karel.row, karel.col, karel_direction[karel.dir]])
        world["trays"] = []
        for tray in self.trays.dump():
            world["trays"].append(tray)
        world["exits"] = []
        for exit in self.exits.dump():
            world["exits"].append(exit)
        return world

    def respawn(self, handle):
        self.karels[handle] = copy.copy(self.karels_initial[handle])
