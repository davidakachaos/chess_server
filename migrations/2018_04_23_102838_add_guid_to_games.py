from orator.migrations import Migration


class AddGuidToGames(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.table('games') as table:
            table.string('guid').nullable()

    def down(self):
        """
        Revert the migrations.
        """
        with self.schema.table('games') as table:
            table.drop_column('guid')
