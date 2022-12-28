import logging
from functools import partial

import psycopg2
import psycopg2.extras
import psycopg2 as Database
from sqlalchemy import event
from sqlalchemy.dialects import postgresql
from sqlalchemy.pool import manage, QueuePool

from django.conf import settings
from django.dispatch import Signal
from django.utils import version
from django.utils.asyncio import async_unsafe
from django.db.backends.postgresql.base import DatabaseWrapper as Psycopg2DatabaseWrapper
from django.db.backends.postgresql.creation import DatabaseCreation as Psycopg2DatabaseCreation

__all__ = ["DatabaseWrapper"]

log = logging.getLogger('django')
pool_disposed = Signal()


def _log(message, *args):
    log.debug(message, *args)


# Only hook up the listeners if we are in debug mode.
event.listen(QueuePool, 'checkout', partial(_log, 'retrieved from pool'))
event.listen(QueuePool, 'checkin', partial(_log, 'returned to pool'))
event.listen(QueuePool, 'connect', partial(_log, 'new connection'))


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


class DatabaseWrapper(Psycopg2DatabaseWrapper):
    POOL_SETTINGS = {
        'pre_ping': True,
        'echo': True,
        'timeout': None,
        'recycle': 60 * 60,
        'pool_size': 10,
        'max_overflow': 15,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pool = None
        self._pool_connection = None
        self.creation = DatabaseCreation(self)

    @property
    def db_pool(self):
        pool_setting = {}
        pool_options = self.settings_dict.get('POOL_OPTIONS', {})

        for key, value in self.POOL_SETTINGS.items():
            if key.upper() in pool_options:
                pool_setting.setdefault(key.lower(), pool_options[key.upper()])
            else:
                pool_setting.setdefault(key.lower(), value)

        if hasattr(self, "_db_pool"):
            pool = getattr(self, "_db_pool")
        else:
            pool_setting["poolclass"] = QueuePool
            pool_setting['dialect'] = postgresql.dialect(dbapi=psycopg2)

            pool = manage(Database, **pool_setting)
            setattr(self, "_db_pool", pool)

        log.info("%s.DatabaseWrapper <db_pool>: %s", self.__class__.__module__, pool)
        return pool

    def _close(self):
        if self._pool_connection is not None:
            if not self.is_usable():
                self._pool_connection.invalidate()

            with self.wrap_database_errors:
                return self._pool_connection.close()

    @async_unsafe
    def create_cursor(self, name=None):
        if name:
            # In autocommit mode, the cursor will be used outside of a
            # transaction, hence use a holdable cursor.
            cursor = self._pool_connection.cursor(name, scrollable=False, withhold=self.connection.autocommit)
        else:
            cursor = self._pool_connection.cursor()

        cursor.tzinfo_factory = self.tzinfo_factory if settings.USE_TZ else None
        return cursor

    @async_unsafe
    def get_new_connection(self, conn_params):
        if not self._pool:
            self._pool = self.db_pool.get_pool(**conn_params)

        # get new connection through pool, not creating a new one outside.
        self._pool_connection = self._pool.connect()
        conn = self._pool_connection.connection  # dbapi connection

        options = self.settings_dict['OPTIONS']
        try:
            self.isolation_level = options['isolation_level']
        except KeyError:
            self.isolation_level = conn.isolation_level
        else:
            # Set the isolation level to the value from OPTIONS.
            if self.isolation_level != conn.isolation_level:
                conn.set_session(isolation_level=self.isolation_level)

        django_version = version.get_version_tuple(version.get_version())
        if django_version >= (3, 1, 1):
            psycopg2.extras.register_default_jsonb(conn_or_curs=conn, loads=lambda x: x)

        return conn

    def tzinfo_factory(self, offset):
        return self.timezone

    def _commit(self):
        log_args = (self.__class__.__module__, self.connection, self.is_usable())
        log.info("%s.DatabaseWrapper._commit -> connection: %s, is_usable: %s", *log_args)

        if self.connection is not None and self.is_usable():
            with self.wrap_database_errors:
                return self.connection.commit()

    def _rollback(self):
        if self.connection is not None and self.is_usable():
            with self.wrap_database_errors:
                return self.connection.rollback()

    def dispose(self):
        """Dispose of the pool for this instance, closing all connections."""
        self.close()
        self._pool_connection = None

        # _DBProxy.dispose doesn't actually call dispose on the pool
        if self._pool:
            self._pool.dispose()
            self._pool = None

        conn_params = self.get_connection_params()
        self.db_pool.dispose(**conn_params)
        pool_disposed.send(sender=self.__class__, connection=self)

    def is_usable(self):
        if not self.connection:
            return False

        return not self.connection.closed


