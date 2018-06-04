# from threading import Thread, currentThread
# from socket import SHUT_RDWR
import logging
import pickle
import socketserver

from models.game import Game
from models.player import Player
from game_keeper import GameNotFound, IllegalMove, NotPlayersTurn

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
        self.last_log_line = ""

    def _get_player(self, text):
        guid = text.split("|")[-1]
        self.logger.debug(f"Checking player guid {guid}")
        p = Player.where('guid', guid).first()
        if p is None:
            raise NotLoggedIn("Not logged in!")
        return p

    def handle(self):
        """Handle incomming commands.

        Returns
        -------
        reponse to client.

        """
        try:
            data = self.request.recv(4096)
            text = data.decode('utf-8')
            self.logger.debug(f"Raw command: {text}")
        except ConnectionResetError as e:
            self.logger.error("Client disconnected before sending command!")
            return

        if len(text) < 1:
            self.logger.debug("Unknown command!")
            self.request.sendall('invalid'.encode("utf8"))
            self.request.close()
            return
        try:
            cmd = text.split("|")[0]
            method_name = f"_handle_{cmd}"
            method = getattr(self, method_name)
            # self.logger.debug(f"exec: {method_name}")
            return method(text)
        except NotLoggedIn as e:
            self.request.sendall('NOT LOGGED IN!'.encode("utf8"))
        except AttributeError as e:
            self.logger.debug("Unknown command!")
            self.request.sendall('invalid'.encode("utf8"))
            self.request.close()
            return

    def _handle_dequeue(self, text):
        player = self._get_player(text)
        if self.server.game_keeper.dequeue_player(player):
            self.request.sendall("dequeued".encode("utf8"))
        else:
            self.request.sendall("player_not_in_queue".encode("utf8"))

    def _handle_getboardstate(self, text):
        player = self._get_player(text)
        gguid = text.split("|")[1]
        state = self.server.game_keeper.get_game_state(gguid)
        self.request.sendall(pickle.dumps(state))

    def _handle_getboard(self, text):
        self._get_player(text)
        gguid = text.split("|")[1]
        self.logger.info("Loading board for player")
        board = self.server.game_keeper.get_board(gguid)
        self.logger.info(f"Board: {board}")
        self.request.sendall(pickle.dumps(board))

    def _handle_move(self, text):
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

    def _handle_all_games(self, text):
        self.logger.debug('Client wants a list of all games')
        p = self._get_player(text)
        games = p.games_as_white.all() + p.games_as_black.all()
        guids = [g.guid for g in games]
        self.request.sendall("|".join(guids).encode("utf8"))

    def _handle_done_games(self, text):
        self.logger.debug('Client wants a list of old games')
        p = self._get_player(text)
        games = p.games_as_white.all() + p.games_as_black.all()
        games = [g for g in games if g.state != 'in_progress']
        guids = [g.guid for g in games]
        self.request.sendall("|".join(guids).encode("utf8"))

    def _handle_myturn(self, text):
        _, gguid, pguid = text.split('|')
        player = self._get_player(text)
        game = Game.where('guid', gguid).first()
        if game.player_to_play.id == player.id:
            self.request.sendall("True".encode("utf8"))
        else:
            self.request.sendall("False".encode("utf8"))

    def _handle_myside(self, text):
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

    def _handle_queue_up(self, text):
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
