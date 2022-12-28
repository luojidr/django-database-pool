from django.conf import settings
import os


def get_extras(user_defined_extras=None):
    """ Oracle already has OPTIONS specific to cx_Oracle.connection() use
        This adds extra pool and sql logging attributes to the settings

        'homogeneous':1, # 1 = single credentials, 0 = multiple credentials
        Dropped this option to use multiple credentials since if supplied
        to Database.version (ie cx_Oracle) < '5.0.0' it breaks and we want
        separate pools for separate credentials anyhow.
    """
    default_extras = {'min': 4,             # start number of connections
                      'max': 8,             # max number of connections
                      'increment': 1,       # increase by this amount when more are needed
                      'threaded': True,     # server platform optimisation
                      'timeout': 600,       # connection timeout, 600 = 10 mins
                      'log': 0,             # extra logging functionality
                      'logpath': '',        # file system path for oracle.log file
                      'existing': '',       # Type modifications if using existing database data
                      'like': 'LIKEC',      # Use LIKE or LIKEC - Oracle ignores index for LIKEC on older dbs
                      'session': []         # Add session optimisations applied to each fresh connection, eg.
                                            #   ['alter session set cursor_sharing = similar',
                                            #   'alter session set session_cached_cursors = 20']
                      }

    if user_defined_extras and len(user_defined_extras) != 0:
        return user_defined_extras
    elif hasattr(settings, 'DATABASE_EXTRAS'):
        return settings.DATABASE_EXTRAS
    else:
        return default_extras


def get_logger(extras):
    """ Check whether logging is required
        If log level is more than zero then logging is performed
        If log level is DEBUG then logging is printed to screen
        If no logfile is specified then unless its DEBUG to screen its added here
        NB: Log levels are 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
    """

    loglevel = int(extras.get('log', 0))
    if loglevel > 0:
        import logging
        logfile = extras.get('logpath', '')
        if logfile.endswith('.log'):
            (logfile, filename) = os.path.split(logfile)
        else:
            filename = 'oracle.log'
        if os.path.exists(logfile):
            logfile = os.path.join(logfile, filename)
        else:
            logfile = ''
        if not logfile and extras.get('log') > logging.DEBUG:
            logfile = '.'
        if logfile in ['.', '..']:
            logfile = os.path.join(os.path.abspath(os.path.dirname(logfile)), filename)
        # if log file is writable do it
        if not logfile:
            raise Exception('Log path %s not found' % extras.get('logpath', ''))
        else:
            logging.basicConfig(filename=logfile, level=loglevel)
            mylogger = logging.getLogger("oracle_pool")
            mylogger.setLevel(loglevel)
            chandler = logging.StreamHandler()
            chandler.setLevel(loglevel)
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            formatter = logging.Formatter(fmt)
            chandler.setFormatter(formatter)
            mylogger.addHandler(chandler)

            from datetime import datetime

            msg = '''%s #### Started oracle SQL logging at level %s ####''' % (datetime.now(), loglevel)
            mylogger.info(msg)
            return mylogger
    else:
        # 'No logging set'
        pass

    # Add sql logging for all requests if DEBUG level
    if extras.get('log') == 10 or settings.DEBUG:
        # Add middleware if needed
        middleware_classes = list(settings.MIDDLEWARE_CLASSES)
        middleware_classes.append('database_pool.oracle.log_sql.SQLLogMiddleware')
        settings.MIDDLEWARE_CLASSES = tuple(middleware_classes)

