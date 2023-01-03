from django.db.backends.postgresql.creation import DatabaseCreation as Psycopg2DatabaseCreation

__all__ = ["DatabaseCreation"]


class DatabaseCreation(Psycopg2DatabaseCreation):
    def _clone_test_db(self, *args, **kw):
        self.connection.dispose()
        super(DatabaseCreation, self)._clone_test_db(*args, **kw)

    def create_test_db(self, *args, **kw):
        self.connection.dispose()
        super(DatabaseCreation, self).create_test_db(*args, **kw)

    def destroy_test_db(self, *args, **kw):
        """Ensure connection pool is disposed before trying to drop database."""
        self.connection.dispose()
        super(DatabaseCreation, self).destroy_test_db(*args, **kw)
