from orator.migrations import Migration


class CreateGamesTable(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.create('games') as table:
            table.increments('id')
            table.integer('black_player_id').unsigned()
            table.foreign('black_player_id').references(
                'id').on('players').on_delete('cascade')
            table.integer('white_player_id').unsigned()
            table.foreign('white_player_id').references(
                'id').on('players').on_delete('cascade')
            table.string('board_state').nullable()
            table.enum('state', ['in_progress',
                                 'white_won', 'black_won', 'draw'])
            table.timestamps()

    def down(self):
        """
        Revert the migrations.
        """
        self.schema.drop('games')
