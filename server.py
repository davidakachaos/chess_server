# Init datbase connection
import logging
import socketserver
import sys

from game_keeper import GameKeeper
from responder import Responder
from time_lord import TimeLord

logging.basicConfig(level=logging.DEBUG,
                    format='%(relativeCreated)6d %(threadName)s %(name)-12s %(levelname)-8s %(message)s',
                    )

# Multithreaded Python server : TCP Server Socket Program Stub
TCP_IP = '127.0.0.1'  # '0.0.0.0'
TCP_PORT = 2004


class ChessServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, game_keeper):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(relativeCreated)6d %(threadName)s %(name)-12s %(levelname)-8s %(message)s',
                            )
        self.logger = logging.getLogger('ChessServer')
        self.logger.debug('__init__')
        self.game_keeper = game_keeper
        socketserver.TCPServer.__init__(
            self, server_address, RequestHandlerClass)

    def serve_forever(self, poll_interval=0.5):
        self.logger.debug('waiting for request')
        self.logger.info(
            'Handling requests, press <Ctrl-C> to quit'
        )
        socketserver.TCPServer.serve_forever(self, poll_interval)
        return


if __name__ == "__main__":
    # Set level to error logging for orator
    logging.getLogger('orator.connection.queries').setLevel(logging.ERROR)
    logging.getLogger('orator.database_manager').setLevel(logging.ERROR)

    GAME_KEEPER = GameKeeper()
    GAME_KEEPER.load_games()
    TIME_LORD = TimeLord()
    SERVER = ChessServer((TCP_IP, TCP_PORT), Responder, GAME_KEEPER)
    try:
        TIME_LORD.start(GAME_KEEPER)
        SERVER.logger.info(f"Server booted, tasks: {len(TIME_LORD.TASKS)}")
        SERVER.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        TIME_LORD.stop()
