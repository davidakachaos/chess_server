from orator.migrations import Migration


class AddHashedToplayers(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.table('players') as table:
            table.string('hashed_password').nullable()
            table.string('guid').nullable()

    def down(self):
        """
        Revert the migrations.
        """
        with self.schema.table('players') as table:
            table.drop_column('hashed_password', 'guid')
