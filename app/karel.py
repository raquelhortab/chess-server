import random
import socketIO_client
from flask_socketio import emit

class DyingException(Exception):
    pass


class Karel:
    instructions = dict(
        move=1, turnLeft=1, putBeeper=1, pickBeeper=1,
        turnRight=2, turnAround=2, paintCorner=2,
        putBeeperInTray=1, pickBeeperFromTray=1,
        exit=1, removeWall=1, createWall=1,
        convertBeeperIntoMine=1
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
        trayIsMine=1,
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

    def turnAround(self):
        self.karel_model.turn_right(self.handle)
        self.karel_model.turn_right(self.handle)
        self.__send_command("turnRight")
        self.__send_command("turnRight")

    def frontIsClear(self):
        return self.karel_model.front_is_clear(self.handle)

    def frontIsBlocked(self):
        return not self.karel_model.front_is_clear(self.handle)

    def leftIsClear(self):
        self.karel_model.turn_left(self.handle)
        response = self.karel_model.front_is_clear(self.handle)
        self.karel_model.turn_right(self.handle)
        return response

    def rightIsClear(self):
        self.karel_model.turn_right(self.handle)
        response = self.karel_model.front_is_clear(self.handle)
        self.karel_model.turn_left(self.handle)
        return response

    def leftIsBlocked(self):
        return not self.leftIsClear()

    def rightIsBlocked(self):
        return not self.rightIsClear()

    def beepersPresent(self):
        return self.karel_model.beepers_present(self.handle)

    def noBeepersPresent(self):
        return not self.beepersPresent()

    def beepersInBag(self):
        return bool(self.karel_model.get_num_beepers(self.handle))

    def noBeepersInBag(self):
        return not self.beepersInBag()

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

    def trayIsMine(self):
        if self.trayPresent():
            return self.karel_model.tray_is_mine(self.handle)
        else:
            self.__send_command("die")
            raise DyingException("No trays present")

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
        if self.karel_model.front_is_bomb(self.handle):
            self.karel_model.explode_bomb(self.handle)
            self.__send_command("move")
            self.__send_command("removeBomb")
            self.__send_command("die")
            raise DyingException("Boom!")

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

    def createWall(self):
        if self.karel_model.create_wall(self.handle):
            self.__send_command("createWall")
        else:
            self.__send_command("die")
            raise DyingException("Can't create wall")

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

    def convertBeeperIntoMine(self):
        if self.karel_model.convert_beeper_into_bomb(self.handle):
            self.__send_command("convertBeeperIntoMine")
        else:
            self.__send_command("die")
            raise DyingException("No beepers to convert")

    def black_code(self):
        turns = {
          1: 'turnRight',
          2: 'turnAround',
          3: 'turnLeft'
        }
        second_turn = turns[random.randint(1,3)]

        return """function main(){
          repeat( %s ) {
              while( frontIsClear() ) {
                  move();
                  if ( beepersPresent() ) {
                      pickBeeper();
                      convertBeeperIntoMine();
                  }
                  if( frontIsBlocked() ) {
                      if ( isRemovableWall() ) {
                          removeWall();
                      }
                  }
               }
              %s();
              while( frontIsBlocked() ) {
                  turnLeft();
               }
            }
          }""" % (random.randint(1,3), second_turn)


INFINITY = 100000000
