from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql as MySQLDialect
from django.db.backends.mysql import base
from database_pool.core import mixins


class DatabaseWrapper(mixins.DBPoolWrapperMixin, base.DatabaseWrapper):
    class SQLAlchemyDialect(MySQLDialect):
        pass

    def _set_dbapi_autocommit(self, autocommit):
        """ self.connection: <class 'sqlalchemy.pool.base._ConnectionFairy'> """
        args = (self.vendor, self.connection, autocommit)
        self.logger.info("[%s] DatabaseWrapper._set_dbapi_autocommit conn: %s, autocommit: %s", *args)

        self.connection.connection.autocommit(autocommit)
