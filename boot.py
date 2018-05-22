from models.game import Game
from models.player import Player
from game_keeper import GameKeeper

print("Loaded models + GameKeeper")

g = Game.first()
gk = GameKeeper()
