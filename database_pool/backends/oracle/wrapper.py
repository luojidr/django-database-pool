"""
Oracle pooled connection database backend for Django.
Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

import os
import _thread as thread

try:
    import cx_Oracle as Database
    from cx_Oracle import DatabaseError
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading cx_Oracle module: %s" % e)

try:
    from django.db.backends.signals import connection_created
except:
    connection_created = None

from django.conf import settings
from django.utils.encoding import smart_str
from django.utils.encoding import force_str as force_unicode
from django.db.backends.base.validation import BaseDatabaseValidation

# Makes it explicit where the default oracle versions of these components are used
from django.db.backends.oracle.base import DatabaseFeatures as OracleDatabaseFeatures
from django.db.backends.oracle.base import DatabaseOperations as OracleDatabaseOperations
from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper
from django.db.backends.oracle.client import DatabaseClient as OracleDatabaseClient
from django.db.backends.oracle.introspection import DatabaseIntrospection as OracleDatabaseIntrospection
from django.db.backends.oracle.base import FormatStylePlaceholderCursor as OracleFormatStylePlaceholderCursor

from .creation import DatabaseCreation
from .utils import get_logger, get_extras

# Check whether cx_Oracle was compiled with the WITH_UNICODE option.  This will also be True in Python 3.0.
if int(Database.version.split('.', 1)[0]) >= 5 and not hasattr(Database, 'UNICODE'):
    convert_unicode = force_unicode
else:
    convert_unicode = smart_str

# Oracle takes client-side character set encoding from the environment.
os.environ['NLS_LANG'] = '.UTF8'


class DatabaseFeatures(OracleDatabaseFeatures):
    """ Add extra options from default Oracle ones
        Plus switch off save points and id return
        See
        http://groups.google.com/group/django-developers/browse_thread/thread/bca33ecf27ff5d63
        Savepoints could be turned on but are not needed
        and since they may impact performance they are turned off here
    """
    uses_savepoints = False
    can_return_id_from_insert = False
    allows_group_by_ordinal = False
    supports_tablespaces = True
    uses_case_insensitive_names = True
    time_field_needs_date = True
    date_field_supports_time_value = False


class DatabaseWrapper(OracleDatabaseWrapper):
    # https://bitbucket.org/edcrewe/django-oraclepool
    """ This provides the core connection object wrapper
        for cx_Oracle's pool handling.
        The code is mostly taken from
        http://code.djangoproject.com/ticket/7732 by halturin
    """

    poolprops = {
        'homogeneous': '',
        'increment': '',
        'max': '',
        'min': '',
        'busy': '',
        'opened': '',
        'name': '',
        'timeout': '',
        'tnsentry': ''
    }
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': "LIKEC %s ESCAPE '\\'",
        'icontains': "LIKEC UPPER(%s) ESCAPE '\\'",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKEC %s ESCAPE '\\'",
        'endswith': "LIKEC %s ESCAPE '\\'",
        'istartswith': "LIKEC UPPER(%s) ESCAPE '\\'",
        'iendswith': "LIKEC UPPER(%s) ESCAPE '\\'",
    }
    oracle_version = None

    def __init__(self, *args, **kwargs):
        """ Set up the various database components
            Oracle prefixed classes use the standard Oracle
            version
        """
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        user_defined_extras = self.settings_dict['EXTRAS'] if 'EXTRAS' in self.settings_dict else {}
        self.extras = get_extras(user_defined_extras)
        self.logger = get_logger(self.extras)

        like_operators = ['contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith']
        if self.extras.get('like', 'LIKEC') != 'LIKEC':
            for key in like_operators:
                self.operators[key] = self.operators[key].replace('LIKEC', self.extras['like'])

        self.features = DatabaseFeatures(self)
        self.ops = OracleDatabaseOperations(self)
        self.client = OracleDatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = OracleDatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)
        self.autocommit = True

    def get_config(self):
        """ Report the oracle connection and pool data see
            http://cx-oracle.sourceforge.net/html/session_pool.html#sesspool
        """
        pool = self._get_pool()
        if pool:
            for key in self.poolprops.keys():
                try:
                    self.poolprops[key] = getattr(pool, key, '')
                except:
                    pass
        else:
            self.poolprops['name'] = 'Session pool not found'

        return self.poolprops

    def _get_pool(self):
        """ Get the connection pool or create it if it doesnt exist
            Add thread lock to prevent server initial heavy load creating multiple pools
        """
        pool_name = '_pool_%s' % getattr(self, 'alias', 'common')

        if not hasattr(self.__class__, pool_name):
            lock = thread.allocate_lock()
            lock.acquire()

            if not hasattr(self.__class__, pool_name):
                if self.extras['threaded']:
                    Database.OPT_Threading = 1
                else:
                    Database.OPT_Threading = 0
                # Use 1.2 style dict if its there, else make one
                try:
                    settings_dict = self.creation.connection.settings_dict
                except:
                    settings_dict = None

                if not settings_dict.get('NAME', ''):
                    settings_dict = {'HOST': settings.DATABASE_HOST,
                                     'PORT': settings.DATABASE_PORT,
                                     'NAME': settings.DATABASE_NAME,
                                     'USER': settings.DATABASE_USER,
                                     'PASSWORD': settings.DATABASE_PASSWORD,
                                     }
                if len(settings_dict.get('HOST', '').strip()) == 0:
                    settings_dict['HOST'] = 'localhost'
                if len(settings_dict.get('PORT', '').strip()) != 0:
                    dsn = Database.makedsn(str(settings_dict['HOST']),
                                           int(settings_dict['PORT']),
                                           str(settings_dict.get('NAME', '')))
                else:
                    dsn = settings_dict.get('NAME', '')

                try:
                    pool = Database.SessionPool(str(settings_dict.get('USER', '')),
                                                str(settings_dict.get('PASSWORD', '')),
                                                dsn,
                                                int(self.extras.get('min', 4)),
                                                int(self.extras.get('max', 8)),
                                                int(self.extras.get('increment', 1)),
                                                threaded=self.extras.get('threaded', True))
                except Exception as err:
                    pool = None

                if pool:
                    if self.extras.get('timeout', 0):
                        pool.timeout = self.extras['timeout']
                    setattr(self.__class__, pool_name, pool)
                else:
                    msg = """##### Database '%(NAME)s' login failed or database not found ##### 
                             Using settings: %(USER)s @ %(HOST)s:%(PORT)s / %(NAME)s  
                             Django start up cancelled
                          """ % settings_dict
                    msg += '\n##### DUE TO ERROR: %s\n' % err
                    if self.logger:
                        self.logger.critical(msg)
                    else:
                        print(msg)
                    return None
                lock.release()
        return getattr(self.__class__, pool_name)

    pool = property(_get_pool)

    def _valid_connection(self):
        return self.connection is not None

    def _connect_string(self):
        settings_dict = self.settings_dict
        if not settings_dict['HOST'].strip():
            settings_dict['HOST'] = 'localhost'

        if settings_dict['PORT'].strip():
            dsn = Database.makedsn(settings_dict['HOST'],
                                   int(settings_dict['PORT']),
                                   settings_dict['NAME'])
        else:
            dsn = settings_dict['NAME']

        return "%s/%s@%s" % (settings_dict['USER'], settings_dict['PASSWORD'], dsn)

    def _cursor(self, settings=None):
        """ Get a cursor from the connection pool """
        cursor = None
        if self.pool is not None:
            if self.connection is None:

                # Get a connection, after confirming that is a valid connection
                self.connection = self._get_alive_connection()

                if connection_created:
                    # Assume acquisition of existing connection = create for django signal
                    connection_created.send(sender=self.__class__)
                if self.logger:
                    self.logger.info("Acquire pooled connection \n%s\n" % self.connection.dsn)

                cursor = FormatStylePlaceholderCursor(self.connection, self.logger)

                # In case one connection in the pool dies we need to retry others in the pool
                retry = 0
                max_retry = self.extras.get('min', 4)

                while retry < max_retry:
                    try:
                        cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD' "  
                                       "NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
                        retry = max_retry
                    except Database.Error as error:
                        if self.logger:
                            self.logger.warn("Failed to set session date due to error: %s" % error)
                        # If we have exhausted all of our connections in our pool raise the error
                        if retry == max_retry - 1:
                            if self.logger:
                                self.logger.critical("Exhausted %d connections in the connection pool")
                            raise

                    retry += 1

                if self.extras.get('session', []):
                    for sql in self.extras['session']:
                        cursor.execute(sql)

                try:
                    # There's no way for the DatabaseOperations class to know the
                    # currently active Oracle version, so we do some setups here.
                    # TODO: Multi-db support will need a better solution (a way to
                    # communicate the current version).
                    self.oracle_version = int(self.connection.version.split('.')[0])
                    # Django 1.7 or earlier has regex function changer for old Oracle
                    if self.oracle_version <= 9:
                        if hasattr(self.ops, 'regex_lookup_9'):
                            self.ops.regex_lookup = self.ops.regex_lookup_9
                    elif hasattr(self.ops, 'regex_lookup_10'):
                        self.ops.regex_lookup = self.ops.regex_lookup_10
                except ValueError as err:
                    if self.logger:
                        self.logger.warn(str(err))

                try:
                    self.connection.stmtcachesize = 20
                except:
                    # Django docs specify cx_Oracle version 4.3.1 or higher, but
                    # stmtcachesize is available only in 4.3.2 and up.
                    pass
            else:
                cursor = FormatStylePlaceholderCursor(self.connection, self.logger)
        else:
            if self.logger:
                self.logger.critical('Pool couldnt be created - please check your Oracle connection or credentials')
            else:
                raise Exception('Pool couldnt be created - please check your Oracle connection or credentials')
        if not cursor:
            cursor = FormatStylePlaceholderCursor(self.connection, self.logger)
        # Default arraysize of 1 is highly sub-optimal.
        cursor.arraysize = 100
        return cursor

    def get_new_connection(self, conn_params):
        """ Want a pooled connection """
        # conn_string = convert_unicode(self._connect_string())
        # return Database.connect(conn_string, **conn_params)
        return self._get_alive_connection()

    def create_cursor(self, name=None):
        return self._cursor()

    def _get_alive_connection(self):
        """ Get a connection from the connection pool.
            Make sure it's a valid connection (using ping()) before returning it.
            Pass on the autocommit -> needs this True for django 1.6 to use atomic transactions
        """
        connection_ok = False
        sanity_check = 0
        sanity_threshold = self.extras.get('max', 10)

        while not connection_ok:
            new_conn = self.pool.acquire()

            try:
                new_conn.ping()
                connection_ok = True
            except Database.Error as error:
                sanity_check += 1
                if sanity_check > sanity_threshold:
                    raise Exception('Could not get a valid/alive connection from the connection pool.')

                if self.logger:
                    self.logger.critical('Found a dead connection.  Dropping from pool.')
                self.pool.drop(new_conn)

            with self.wrap_database_errors:
                new_conn.autocommit = self.autocommit

        return new_conn

    def close(self):
        """ Releases connection back to pool """
        if self.connection is not None:
            if self.logger:
                self.logger.debug("Release pooled connection\n%s\n" % self.connection.dsn)
            try:
                self.pool.release(self.connection)
            except Database.OperationalError as error:
                if self.logger:
                    self.logger.debug("Release pooled connection failed due to: %s" % str(error))
            finally:
                self.connection = None

    def _savepoint_commit(self, sid):
        """ Oracle doesn't support savepoint commits.  Ignore them. """
        pass

    def _rollback(self):
        if self.connection:
            try:
                self.connection.rollback()
            except Database.OperationalError as error:
                if self.logger:
                    self.logger.debug("Rollback failed due to:  %s" % str(error))


class FormatStylePlaceholderCursor(OracleFormatStylePlaceholderCursor):
    """ Added just to allow use of % for like queries without params
        and use of logger if present.
    """

    def __init__(self, connection, logger):
        OracleFormatStylePlaceholderCursor.__init__(self, connection)
        self.logger = logger

    def cleanquery(self, query, args=None):
        """ cx_Oracle wants no trailing ';' for SQL statements.  For PL/SQL, it
            it does want a trailing ';' but not a trailing '/'.  However, these
            characters must be included in the original query in case the query
            is being passed to SQL*Plus.

            Split out this as a function and allowed for no args so
            % signs can be used in the query without requiring parameterization
        """
        # if query.find('INSERT') > -1:
        #     raise Exception(query)   # params[8])

        if query.endswith(';') or query.endswith('/'):
            query = query[:-1]

        if not args:
            return convert_unicode(query, self.charset)
        else:
            try:
                return convert_unicode(query % tuple(args), self.charset)
            except TypeError as error:
                err = 'Parameter parsing failed due to error %s for query: %s' % (error, query)

                if self.logger:
                    self.logger.critical(err)
                else:
                    raise Exception(err)

    def execute(self, query, params=()):
        if params is None:
            args = None
        else:
            params = self._format_params(params)
            args = [(':arg%d' % i) for i in range(len(params))]

        query = self.cleanquery(query, args)
        self._guess_input_sizes([params])

        try:
            return self.cursor.execute(query, self._param_generator(params))
        except Database.Error as error:
            # cx_Oracle <= 4.4.0 wrongly raises a Database.Error for ORA-01400.
            if error.args[0].code == 1400 and not isinstance(error,
                                                             Database.IntegrityError):
                error = Database.IntegrityError(error.args[0])
            err = '%s due to query:%s' % (error, query)
            if self.logger:
                self.logger.critical(err)
            else:
                raise Exception(err)

    def executemany(self, query, params=()):
        try:
            args = [(':arg%d' % i) for i in range(len(params[0]))]
        except (IndexError, TypeError):
            # No params given, nothing to do
            return None

        query = self.cleanquery(query, args)
        formatted = [self._format_params(i) for i in params]
        self._guess_input_sizes(formatted)

        try:
            return self.cursor.executemany(query, [self._param_generator(p) for p in formatted])
        except Database.Error as error:
            # cx_Oracle <= 4.4.0 wrongly raises a Database.Error for ORA-01400.
            if error.args[0].code == 1400 and not isinstance(error,
                                                             Database.IntegrityError):
                error = Database.IntegrityError(error.args[0])
            if self.logger:
                self.logger.critical('%s due to query: %s' % (error, query))
            else:
                raise
