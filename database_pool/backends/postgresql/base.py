from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from django.db.backends.postgresql.base import DatabaseWrapper as Pg2DatabaseWrapper

from database_pool.core.mixins import DBPoolWrapperMixin

__all__ = ["DatabaseWrapper"]


class DatabaseWrapper(DBPoolWrapperMixin, Pg2DatabaseWrapper):
    class SQLAlchemyDialect(PGDialect_psycopg2):
        pass

