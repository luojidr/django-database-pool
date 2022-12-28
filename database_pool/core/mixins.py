import logging
import threading
from copy import deepcopy
from sqlalchemy import pool

try:
    from django.utils.translation import ugettext_lazy as _
except ImportError:
    from django.utils.translation import gettext_lazy as _

from database_pool.core.exceptions import PoolDoesNotExist

__all__ = ["DBPoolWrapperMixin"]


class DBConnectionPool(dict):
    # The default parameters of pool
    DEFAULT_POOL_PARAMS = {
        'pre_ping': True,
        'echo': True,
        'timeout': None,
        'recycle': 60 * 60,
        'pool_size': 10,
        'max_overflow': 15,
    }

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(DBConnectionPool, cls).__new__(cls, *args, **kwargs)

            # Important:
            # acquire this lock before modify pool_container
            cls._instance.lock = threading.Lock()

        return cls._instance

    def put(self, pool_name, pool):
        self[pool_name] = pool

    def get(self, pool_name):
        try:
            return self[pool_name]
        except KeyError:
            raise PoolDoesNotExist(_('No such pool: {pool_name}').format(pool_name=pool_name))


class DBPoolWrapperMixin:
    # the pool's container, for maintaining the pools
    conn_pool = DBConnectionPool()
    logger = logging.getLogger("django")

    def _set_dbapi_autocommit(self, autocommit):
        args = (self.vendor, self.__class__.__name__, self.connection, autocommit)
        self.logger.info("[%s] %s._set_dbapi_autocommit conn: %s, autocommit: %s", *args)

        self.connection.connection.autocommit = autocommit

    def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
            try:
                self._set_dbapi_autocommit(autocommit)
            except Exception as exc:
                self.logger.error('Unable to set autocommit mode of %s(%s) to %s, caused by: %s',
                                  self.vendor, self.alias, autocommit, exc)
                raise exc from None

    def _get_dialect(self):
        dialect = self.SQLAlchemyDialect(dbapi=self.Database)
        return dialect

    def _get_new_connection(self, conn_params):
        # method of connection initiation defined by django
        # django.db.backends.<database>.base.DatabaseWrapper
        get_new_connection = super(DBPoolWrapperMixin, self).get_new_connection

        # method of connection initiation defined by
        # dj_db_conn_pool.backends.<database>.base.DatabaseWrapper
        return get_new_connection(conn_params)

    def get_new_connection(self, conn_params):
        """
        override django.db.backends.<database>.base.DatabaseWrapper.get_new_connection to
        change the default behavior of getting new connection to database, we maintain
        conn_pool who contains the connection pool of each database here
        when django call this method to get new connection, we check whether there exists
        the pool of this database(self.alias)
        if the target pool doesn't exist, we will create one
        then grab one connection from the pool and return it to django
        :return: connection of pool
        """
        with self.conn_pool.lock:
            # acquire the lock, check whether there exists the pool of current database
            # note: the value of self.alias is the name of current database, one of setting.DATABASES
            if self.alias not in self.conn_pool:
                # self.alias's pool doesn't exist, time to create it

                # make a copy of default parameters
                pool_params = deepcopy(self.conn_pool.DEFAULT_POOL_PARAMS)

                # parse parameters of current database from self.settings_dict
                pool_setting = {
                    # transform the keys in POOL_OPTIONS to upper case
                    # to fit sqlalchemy.pool.QueuePool's arguments requirement
                    key.lower(): value
                    # traverse POOL_OPTIONS to get arguments
                    for key, value in
                    # self.settings_dict was created by Django
                    # is the connection parameters of self.alias
                    self.settings_dict.get('POOL_OPTIONS', {}).items()
                    # There are some limits of self.alias's pool's option(POOL_OPTIONS):
                    # the keys in POOL_OPTIONS must be capitalised
                    # and the keys's lowercase must be in conn_pool.pool_default_params
                    if key == key.upper() and key.lower() in self.conn_pool.DEFAULT_POOL_PARAMS
                }

                # replace pool_params's items with pool_setting's items
                # to import custom parameters
                pool_params.update(**pool_setting)

                # now we have all parameters of self.alias
                # create self.alias's pool
                alias_pool = pool.QueuePool(
                    # super().get_new_connection was defined by
                    # db_pool.backends.<database>.base.DatabaseWrapper or
                    # django.db.backends.<database>.base.DatabaseWrapper
                    # the method of connection initiation
                    lambda: self._get_new_connection(conn_params),
                    # SQLAlchemy use the dialect to maintain the pool
                    dialect=self._get_dialect(),
                    # parameters of self.alias
                    **pool_params
                )

                self.logger.info(_("Alias: [%s]'s pool has been created, parameter: %s"), self.alias, pool_params)

                # pool has been created
                # put into conn_pool for reusing
                self.conn_pool.put(self.alias, alias_pool)

        # get self.alias's pool from conn_pool
        db_pool = self.conn_pool.get(self.alias)
        self.logger.info(_("DbPool: %s"), db_pool)

        # get one connection from the pool
        conn = db_pool.connect()

        self.logger.info(_("Alias: got [%s]'s connection from pool, conn: %s, type: %s"), self.alias, conn, type(conn))
        return conn

    def close(self, *args, **kwargs):
        conn = getattr(self.connection, 'connection', None)
        self.logger.info(_("release %s's connection %s to its pool"), self.alias, conn)

        return super(DBPoolWrapperMixin, self).close(*args, **kwargs)
