from repeated_timer import RepeatedTimer


class TimeLord(object):
    """Keeps track of timed functions in the server."""
    TASKS = []

    def start(self, GAME_KEEPER):
        self.TASKS.append(RepeatedTimer(
            20, GAME_KEEPER.create_games_for_queue))
        self.TASKS.append(RepeatedTimer(10, GAME_KEEPER.check_current_games))

    def stop(self):
        for task in self.TASKS:
            task.stop()
