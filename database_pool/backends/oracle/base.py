try:
    from cx_Oracle import DatabaseError
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading cx_Oracle module: %s" % e)

from sqlalchemy.dialects.oracle.cx_oracle import OracleDialect
from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper

from database_pool.core.mixins import DBPoolWrapperMixin


class DatabaseWrapper(DBPoolWrapperMixin, OracleDatabaseWrapper):
    class SQLAlchemyDialect(OracleDialect):
        def do_ping(self, dbapi_connection):
            try:
                return super(OracleDialect, self).do_ping(dbapi_connection)
            except DatabaseError:
                return False

