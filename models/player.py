from orator import Model
from .game import Game
from orator.orm import has_many
import hashlib


class Player(Model):

    __fillable__ = ['name']

    @has_many('white_player_id')
    def games_as_white(self):
        return Game

    @has_many('black_player_id')
    def games_as_black(self):
        return Game

    def _update_pass(self):
        if self.hashed_password is None:
            self.hashed_password = hashlib.sha224(
                self.password.encode("utf8")).hexdigest()
        if self.guid is None:
            self.guid = hashlib.sha224(
                (str(self.id) + self.name + self.hashed_password).encode("utf8")).hexdigest()
        self.save()
