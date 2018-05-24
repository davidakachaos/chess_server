# from threading import Thread, currentThread
# from socket import SHUT_RDWR
import logging
import pickle
import socketserver

from models.game import Game
from models.player import Player
from game_keeper import GameNotFound, IllegalMove, NotPlayersTurn

logging.basicConfig(level=logging.DEBUG,
                    format='%(name)s: %(message)s',
                    )


class NotLoggedIn(Exception):
    """Raised when a used is not logged in for certain functions."""


class Responder(socketserver.BaseRequestHandler):
    """The responder to client requests."""

    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('Responder')
        # self.logger.debug('__init__')
        socketserver.BaseRequestHandler.__init__(self, request,
                                                 client_address,
                                                 server)
        self.game_keeper = server.game_keeper

    def _get_player(self, text):
        guid = text.split("|")[-1]
        self.logger.debug(f"Checking player guid {guid}")
        p = Player.where('guid', guid).first()
        if p is None:
            raise NotLoggedIn("Not logged in!")
        return p

    def handle(self):
        # self.logger.debug('handle')
        # Misschien moet dit omhoog of ander, maar voor nu volstaat dit.
        data = self.request.recv(4096)

        text = data.decode('utf-8')
        self.logger.debug(f"Raw command: {text}")
        try:
            if text.startswith('login'):
                self._handle_login(text)
            elif text.startswith('register'):
                self._handle_register(text)
            elif text.startswith('current_games'):
                self._handle_current_games(text)
            elif text.startswith('myturn'):
                self._handle_my_turn(text)
            elif text.startswith('myside'):
                self._handle_my_side(text)
            elif text.startswith('opponent_name'):
                self._handle_opponent_name(text)
            elif text.startswith('queue_up'):
                self._handle_queuing_up(text)
            elif text.startswith('dequeue'):
                self._handle_dequeue(text)
            elif text.startswith('move'):
                self._handle_move_for_game(text)
            elif text.startswith('getboardstate'):
                self._handle_getboardstate(text)
            elif text.startswith('getboard'):
                self._handle_get_board(text)
            elif text.startswith('current_game_count'):
                self.request.sendall(
                    str(self.server.game_keeper.current_game_count()).encode("utf8"))
            else:
                self.logger.debug("Unknown command!")
                self.request.sendall('invalid'.encode("utf8"))
                # self.request.close()
        except NotLoggedIn as e:
            self.request.sendall('NOT LOGGED IN!'.encode("utf8"))
        finally:
            self.request.close()

    def _handle_dequeue(self, text):
        player = self._get_player(text)
        if self.server.game_keeper.dequeue_player(player):
            self.request.sendall("dequeued".encode("utf8"))
        else:
            self.request.sendall("player_not_in_queue".encode("utf8"))

    def _handle_getboardstate(self, text):
        player = self._get_player(text)
        gguid = text.split("|")[1]
        state = self.server.game_keeper.check_game_state(gguid)
        self.request.sendall(pickle.dumps(state))

    def _handle_get_board(self, text):
        player = self._get_player(text)
        gguid = text.split("|")[1]
        board = self.server.game_keeper.get_board(gguid)
        self.request.sendall(pickle.dumps(board))

    def _handle_move_for_game(self, text):
        # text == move|{gameguid}|{move}|{playerguid}
        _, gguid, move, pguid = text.split('|')
        player = self._get_player(text)
        try:
            self.server.game_keeper.make_move(gguid, player, move)
            # move has been made
            self.request.sendall('move_made'.encode("utf8"))
        except GameNotFound as e:
            self.request.sendall('exception|game-not-found'.encode("utf8"))
            self.request.close()
        except IllegalMove as e:
            self.request.sendall('exception|illegal_move'.encode("utf8"))
            self.request.close()
        except NotPlayersTurn as e:
            self.request.sendall('exception|not-players-turn'.encode("utf8"))
            self.request.close()

    def _handle_current_games(self, text):
        self.logger.debug('Client wants a list of current_games')
        p = self._get_player(text)
        games = p.games_as_white.all() + p.games_as_black.all()
        games = [g for g in games if g.state == 'in_progress']
        guids = [g.guid for g in games]
        self.request.sendall("|".join(guids).encode("utf8"))

    def _handle_my_turn(self, text):
        _, gguid, pguid = text.split('|')
        player = self._get_player(text)
        game = Game.where('guid', gguid).first()
        if game.player_to_play.id == player.id:
            self.request.sendall("True".encode("utf8"))
        else:
            self.request.sendall("False".encode("utf8"))

    def _handle_my_side(self, text):
        _, gguid, pguid = text.split('|')
        player = self._get_player(text)
        game = Game.where('guid', gguid).first()
        if game.white_player_id == player.id:
            self.request.sendall("White".encode("utf8"))
        else:
            self.request.sendall("Black".encode("utf8"))

    def _handle_opponent_name(self, text):
        _, gguid, pguid = text.split('|')
        player = self._get_player(text)
        game = Game.where('guid', gguid).first()
        if game.black_player.id == player.id:
            self.request.sendall(f"{game.white_player.name}".encode("utf8"))
        else:
            self.request.sendall(f"{game.black_player.name}".encode("utf8"))

    def _handle_queuing_up(self, text):
        self.logger.debug("Client requesting a random game.")
        p = self._get_player(text)
        game = self.server.game_keeper.new_game(p)
        if game is None:
            self.request.sendall('queued_for_game'.encode("utf8"))
        else:
            self.request.sendall(f"new_game|{game.guid}".encode("utf8"))

    def _handle_login(self, text):
        self.logger.debug("Recieved login request.")
        # login|username|hashed_password
        usr = text.split('|')[1]
        pwd = text.split('|')[2]
        self.logger.debug(f"Username: {usr} // pswd: {pwd} checking...")
        try:
            player = Player.where('name', usr).where(
                'hashed_password', pwd).first_or_fail()
            self.logger.debug("Found player!")
            self.request.sendall(player.guid.encode("utf8"))
        except:
            self.logger.debug("Found no player named that way...")
            self.request.sendall('invalid'.encode("utf8"))

    def _handle_register(self, text):
        import hashlib
        self.logger.debug("Recieved register request.")
        # register|username|password|password_confirm
        usr = text.split('|')[1]
        pwd1 = text.split('|')[2]
        pwd2 = text.split('|')[3]
        if Player.where("name", usr).count() > 0:
            self.request.sendall('username_taken'.encode("utf8"))
            self.request.close()
            return

        if pwd1 != pwd2:
            self.request.sendall('invalid_password'.encode("utf8"))
            self.request.close()
            return

        player = Player()
        player.name = usr
        player.hashed_password = hashlib.sha224(
            pwd1.encode("utf8")).hexdigest()
        player.save()  # Needed to get an ID in the DB
        player.guid = hashlib.sha224(
            (str(player.id) + player.name +
             player.hashed_password).encode("utf8")).hexdigest()
        if player.save():
            self.request.sendall(
                f"register_success|{player.guid}".encode("utf8"))
            self.request.close()
        else:
            self.request.sendall('register_failed!'.encode("utf8"))
            self.request.close()
