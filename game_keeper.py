import chess
import logging
import random

from models.game import Game
from models.player import Player
from time import sleep


class GameNotFound(Exception):
    """Raise when game not found."""


class IllegalMove(Exception):
    """Raise when move is illegal."""


class NotPlayersTurn(Exception):
    """Raise when its not the players turn to move."""


class GameKeeper():
    """A keeper of games between players."""

    def __init__(self):
        """Initialize a new GameKeeper."""
        self.logger = logging.getLogger('GameKeeper')
        self.logger.debug('__init__')
        self._current_games = set()
        self._current_player_queue = set()
        self._games_to_start = {}

    def player_in_queue(self, player):
        """Check if a player is in the current queue for a new game."""
        return player.id in self._current_player_queue

    def dequeue_player(self, player):
        """
        Remove a player from the current queue for new games.

        This will remove a player from the current queue. It will return
        True if the player was in the queue and False if (s)he wasn'tself.

        Args:
            player (Player): The player to remove from the queue.

        Returns:
            boolean: True if the player was in the queue. False if (s)he wasn't

        """
        was_in_q = player.id in self._current_player_queue
        self.remove_player(player)
        if was_in_q:
            return True
        else:
            return False

    def new_game(self, player, opponent=None):
        """Start a new game between players."""
        game = None
        if opponent:
            # Premade game, not adding player to the queue
            # This allows player vs self??
            game = self._setup_game(player, opponent)
            return game
        if player in self._current_player_queue:
            return None  # 'queued'
        if player.id in self._games_to_start.keys():
            # Game has been created, return to client
            gguid = self._games_to_start[player.id]
            # Remove from list
            del self._games_to_start[player.id]
            return self._lookup_game(gguid)
        # We can't create a game, adding player to queue and return none
        self.add_player(player)
        return None

    def create_games_for_queue(self):
        """
        Create new games for the players in queue.

        This will be called once in a while to check the queue. When there are
        enough players in the queue (2 or more) we start making new games.
        """
        self.logger.info("Checking game queue.")
        self.logger.debug(f"Current players in queue: {len(self._current_player_queue)}")
        while len(self._current_player_queue) > 1:
            self.logger.debug('Creating game for clients.')
            player1 = Player.find(random.choice(list(self._current_player_queue)))
            # Prevent player vs self
            available = [
                p for p in self._current_player_queue if player1.id != p]
            player2 = Player.find(random.choice(available))
            game = self._setup_game(player1, player2)
            self._games_to_start[player1.id] = game.guid
            self._games_to_start[player2.id] = game.guid
            self.logger.debug(f"Create another one? {len(self._current_player_queue) > 1}")
            sleep(1)

    def _setup_game(self, player, opponent):
        self.logger.debug(f"Setting up game between {player.name} and {opponent.name}")
        new_game = Game()
        # Randomize starting player
        if random.randint(1, 100) % 2 == 0:
            self.logger.debug(f"{player.name} starts with white")
            new_game.white_player_id = player.id
            new_game.black_player_id = opponent.id
        else:
            self.logger.debug(f"{opponent.name} starts with white")
            new_game.white_player_id = opponent.id
            new_game.black_player_id = player.id
        # Sets up a new game and saves to the DB
        new_game.setup_new()

        self.remove_player(player)
        self.remove_player(opponent)
        self._current_games.add(new_game)
        return new_game

    def _lookup_game(self, guid):
        return Game.where('guid', guid).first()

    def make_move(self, guid, player, move):
        """Make a [move] for a [player] in a chess game.

        Parameters
        ----------
        guid : String
            The id of a game.
        player : Player
            A chess player in that game.
        move : String
            A uci representation of a move to make in the chess game.

        Returns
        -------
        Void
            Nothing if all wend okay, else raises an exception.

        """
        self.logger.debug(f"Recieved move for game {guid}")
        game = self._lookup_game(guid)
        if game is None:
            self.logger.warn(f"No game with guid {guid} found!")
            raise GameNotFound(f"No game with guid {guid} found!")
        board = game.board
        if player.id == game.player_to_play.id:
            # Ok, player may move
            chess_move = chess.Move.from_uci(move)
            if chess_move in board.legal_moves:
                board.push(chess_move)
                game.save_board(board)
                self.logger.info("Board:")
                self.logger.info(board)
            else:
                self.logger.info("Illegal move!")
                raise IllegalMove(f"Illegal move {move}")
        else:
            raise NotPlayersTurn(f"It is not the turn for player {player.id} in game {guid}")

    def get_game_state(self, guid):
        """Return the state of a game.

        Parameters
        ----------
        guid : String
            The unique identifier of a game.

        Returns
        -------
        Hash
            A hash with the state of a game.

        """
        game = self._lookup_game(guid)
        if not game:
            return {}

        board = game.board
        game_state = {}
        game_state['guid'] = guid
        game_state['white_player'] = game.white_player.name
        game_state['black_player'] = game.black_player.name
        game_state['started'] = game.created_at.to_datetime_string()
        game_state['last_move'] = game.updated_at.to_datetime_string()
        game_state['fen'] = board.fen()
        game_state['game_over'] = board.is_game_over()
        game_state['checkmate'] = board.is_checkmate()
        game_state['stalemate'] = board.is_stalemate()
        game_state['insufficient_material'] = board.is_insufficient_material()
        game_state['seventyfive_moves'] = board.is_seventyfive_moves()
        game_state['fivefold_repetition'] = board.is_fivefold_repetition()
        game_state['can_claim_draw'] = board.can_claim_draw()
        game_state['can_claim_fifty_moves'] = board.can_claim_fifty_moves()
        game_state['can_claim_threefold_repetition'] = board.can_claim_threefold_repetition()
        game_state['result'] = None
        if board.is_game_over():
            if board.result()[-1] == '1':
                game_state['result'] = 'Black won'
            elif board.result()[0] == '1':
                game_state['result'] = 'White won'
            else:
                game_state['result'] = 'Draw'

        return game_state

    def get_board(self, guid):
        """Return a board object for a game.

        Parameters
        ----------
        guid : String
            An unique identifier for a chess game.

        Returns
        -------
        chess.Board
            The current board for a chess game.

        """
        game = self._lookup_game(guid)
        if not game:
            return None
        return game.board

    def check_current_games(self):
        """Check all current games for events.

        Returns
        -------
        None
            Returns nothing.

        """
        for game in self._current_games:
            if not game.state == 'in_progress':
                self.logger.debug(f"Checking game {game.id} | {game.state}")
                self.logger.debug(f"  Game ended in {game.state}")
                self._current_games.discard(game)

    def current_game_count(self):
        """Return the count of current games.

        Returns
        -------
        Integer
            The amount of currently running games.

        """
        self.check_current_games()
        return len(self._current_games)

    def load_games(self):
        """Load all games from database to the current games array."""
        self.logger.debug("Loading games...")
        for game in Game.where('state', 'in_progress').get():
            self._current_games.add(game)

    def add_player(self, player):
        """Add player to the waiting queue.

        Parameters
        ----------
        player : Player
            The player to add to the waiting queue.

        """
        self._current_player_queue.add(player.id)

    def remove_player(self, player):
        """Remove a player from the waiting queue.

        Parameters
        ----------
        player : Player
            The player to remove from the waiting queue.

        """
        self._current_player_queue.discard(player.id)
