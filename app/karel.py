import socketIO_client
from flask_socketio import emit

class DyingException(Exception):
    pass


class Karel:
    instructions = dict(
        move=1, turnLeft=1, putBeeper=1, pickBeeper=1,
        turnRight=2, turnAround=2, paintCorner=2,
        putBeeperInTray=1, pickBeeperFromTray=1,
        exit=1, removeWall=1
    )

    predicates = dict(
        frontIsClear=1, frontIsBlocked=1,
        leftIsClear=1, leftIsBlocked=1,
        rightIsClear=1, rightIsBlocked=1,
        beepersPresent=1, noBeepersPresent=1,
        beepersInBag=1, noBeepersInBag=1,
        trayPresent=1, noTrayPresent=1,
        trayFull=1, trayNotFull=1,
        trayEmpty=1, trayNotEmpty=1,
        trayComplete=1, trayNotComplete=1,
        exitPresent=1, noExitPresent=1,
        facingNorth=1, notFacingNorth=1,
        facingEast=1, notFacingEast=1,
        facingSouth=1, notFacingSouth=1,
        facingWest=1, notFacingWest=1,
        isRemovableWall=1,
        cornerColorIs=2, random=2
    )

    def __init__(self, model, game_id, pc_id, handle):
        self.karel_model = model
        self.game_id = game_id
        self.pc_id = pc_id
        self.handle = handle

    def __send_command(self, command):
        msg = '{"handle": "%s", "command": "%s"}' % (self.handle, command)
        emit('command', msg, room=self.game_id)

    def declareWinner(self):
        emit('winner', self.handle, room=self.game_id)

    def turnLeft(self):
        self.karel_model.turn_left(self.handle)
        self.__send_command("turnLeft")

    def turnRight(self):
        self.karel_model.turn_right(self.handle)
        self.__send_command("turnRight")

    def frontIsClear(self):
        return self.karel_model.front_is_clear(self.handle)

    def frontIsBlocked(self):
        return not self.karel_model.front_is_clear(self.handle)

    def beepersPresent(self):
        return self.karel_model.beepers_present(self.handle)

    def beepersInBag(self):
        return bool(self.karel_model.get_num_beepers(self.handle))

    def trayPresent(self):
        return self.karel_model.tray_present(self.handle)

    def noTrayPresent(self):
        return not self.karel_model.tray_present(self.handle)

    def trayFull(self):
        return self.karel_model.tray_full(self.handle)

    def trayNotFull(self):
        return not self.karel_model.tray_full(self.handle)

    def trayEmpty(self):
        return self.karel_model.tray_empty(self.handle)

    def trayNotEmpty(self):
        return not self.karel_model.tray_empty(self.handle)

    def trayComplete(self):
        return self.karel_model.tray_complete(self.handle)

    def trayNotComplete(self):
        return not self.karel_model.tray_complete(self.handle)

    def exitPresent(self):
        return self.karel_model.exit_present(self.handle)

    def noExitPresent(self):
        return not self.karel_model.exit_present(self.handle)

    def facingNorth(self):
        return self.karel_model.facing_north(self.handle)

    def notFacingNorth(self):
        return not self.karel_model.facing_north(self.handle)

    def facingEast(self):
        return self.karel_model.facing_east(self.handle)

    def notFacingEast(self):
        return not self.karel_model.facing_east(self.handle)

    def facingSouth(self):
        return self.karel_model.facing_south(self.handle)

    def notFacingSouth(self):
        return not self.karel_model.facing_south(self.handle)

    def facingWest(self):
        return self.karel_model.facing_west(self.handle)

    def notFacingWest(self):
        return not self.karel_model.facing_west(self.handle)

    def move(self):
        if self.karel_model.move(self.handle):
            self.__send_command("move")
        else:
            self.__send_command("die")
            raise DyingException("Front is blocked")

    def exit(self):
        if self.karel_model.exit(self.handle):
            self.__send_command("exit")
            self.declareWinner()
        else:
            self.__send_command("die")

    def removeWall(self):
        if self.karel_model.remove_wall(self.handle):
            self.__send_command("removeWall")
        else:
            self.__send_command("die")
            raise DyingException("Can't remove wall")

    def isRemovableWall(self):
        return self.karel_model.is_removable_wall(self.handle)

    def pickBeeper(self):
        if self.karel_model.pick_beeper(self.handle):
            self.__send_command("pickBeeper")
        else:
            self.__send_command("die")

    def putBeeper(self):
        if self.karel_model.put_beeper(self.handle):
            self.__send_command("putBeeper")
        else:
            self.__send_command("die")

    def putBeeperInTray(self):
        if self.karel_model.put_beeper_in_tray(self.handle):
            self.__send_command("putBeeperInTray")
        else:
            self.__send_command("die")

    def pickBeeperFromTray(self):
        if self.karel_model.pick_beeper_from_tray(self.handle):
            self.__send_command("pickBeeperFromTray")
        else:
            self.__send_command("die")

    def load_world(self, world):
        self.karel_model.load_world(world)

    def dump_world(self):
        return self.karel_model.dump_world()

    def return_beeper(self, handle):
        return self.karel_model.return_beeper(handle)

    def respawn(self, handle):
        self.karel_model.respawn(handle)


INFINITY = 100000000
