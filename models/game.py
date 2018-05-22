from orator import Model
from orator.orm import belongs_to
from orator.orm import accessor
import chess
import pickle


class Game(Model):
    __fillable__ = ['black_player_id', 'white_player_id']

    def __init__(self, _attributes=None, **attributes):
        super().__init__(_attributes=None, **attributes)

    def load_board(self):
        if self.board_seril is not None:
            board = pickle.loads(self.get_raw_attribute("board_seril"))
        else:
            board = chess.Board(self.board_state)
        return board

    def save_board(self, board):
        self.board_seril = pickle.dumps(board)
        self.save()

    def setup_new(self):
        # Initialize a new game.
        from uuid import uuid4

        self.guid = str(uuid4())
        board_start = chess.STARTING_FEN
        self.board_state = board_start
        self.board_seril = pickle.dumps(chess.Board(board_start))
        self.state = 'in_progress'
        self.save()

    @property
    def board(self):
        return self.load_board()

    @property
    def player_to_play(self):
        # Is it white turns to play?
        if self.board.turn:
            return self.white_player
        else:
            return self.black_player

    @belongs_to('black_player_id')
    def black_player(self):
        from .player import Player
        return Player

    @belongs_to('white_player_id')
    def white_player(self):
        from .player import Player
        return Player
