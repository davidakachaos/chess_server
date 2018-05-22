from orator import DatabaseManager
from orator import Model

DB_CONFIG = {
    'sqlite3': {
        'driver': 'sqlite',
        'database': 'chess_server.db',
        'log_queries': True
    }
}

DATABASE = DatabaseManager(DB_CONFIG)
Model.set_connection_resolver(DATABASE)
