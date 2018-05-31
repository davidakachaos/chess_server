from orator.migrations import Migration


class RemovePlainPassword(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.table('players') as table:
            table.drop_column('password')
            table.string('hashed_password').change()

    def down(self):
        """
        Revert the migrations.
        """
        with self.schema.table('players') as table:
            table.string('hashed_password').nullable().change()
            table.string('password')
