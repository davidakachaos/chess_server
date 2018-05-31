from orator.migrations import Migration


class CreatePlayersTable(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.create('players') as table:
            table.increments('id')
            table.string('name')
            table.string('password')
            table.timestamps()

    def down(self):
        """
        Revert the migrations.
        """
        self.schema.drop('players')
