from django.db.backends.postgresql.creation import DatabaseCreation as Pg2DatabaseCreation

__all__ = ["DatabaseCreation"]


class DatabaseCreation(Pg2DatabaseCreation):
    def _clone_test_db(self, *args, **kw):
        self.connection.dispose()
        super()._clone_test_db(*args, **kw)

    def create_test_db(self, *args, **kw):
        self.connection.dispose()
        super().create_test_db(*args, **kw)

    def destroy_test_db(self, *args, **kw):
        """Ensure connection pool is disposed before trying to drop database."""
        self.connection.dispose()
        super().destroy_test_db(*args, **kw)
