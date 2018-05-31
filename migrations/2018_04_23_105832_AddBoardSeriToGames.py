from orator.migrations import Migration


class AddBoardSeriToGames(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.table('games') as table:
            table.binary('board_seril').nullable()

    def down(self):
        """
        Revert the migrations.
        """
        with self.schema.table('games') as table:
            table.drop_column('board_seril')
