# -*- coding: utf-8 -*-

"""
Django supports long connections natively, but not connection pooling:
. Third-party tools are already available that are more focused on doing better.Django doesn't need to do a full stack.

. Fetching a connection from the pool instead of creating a new connection, returning a connection to the pool
  instead of closing a connection, and then holding the connection for the entire duration of the request is not
  a true connection pool.

  This requires the same number of database connections as the number of workers, and is basically equivalent to
  a long connection except that it can be used in a loop among workers.

  Long connections also have their advantages, eliminating the overhead of new connections, avoiding the complexity of pooling,
  and being suitable for small and medium-sized sites that do not need to manually manage transactions.

. MySQL connections are very lightweight and efficient, and a large number of Web applications do not use connection pooling.


Reference Blog:
    https://lockshell.com/2019/08/28/django-db-connection-pool/
    https://github.com/altairbow/django-db-connection-pool
    https://github.com/lcd1232/django-postgrespool2

Add Configuration:
settings.py:
    INSTALLED_APPS = [
    ......
    database_pool,  # Could be a independent package that not under `apps` package
    ......
    ]
"""

import os
import json
import os.path
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from . import backends

logger = logging.getLogger("django")


def setup():
    databases = settings.DATABASES
    pkg_name = backends.__package__
    app_name = pkg_name.split(".")[0]

    module_pkg = os.path.realpath(backends.__file__)
    backends_module_path = module_pkg.split(os.sep)[:-1]
    relative_module_path = backends_module_path[backends_module_path.index(app_name):]
    engine_pkg_path = ".".join(relative_module_path)

    logger.warning("ORM Pool `backends_module_path`: %s", backends_module_path)
    logger.warning("ORM Pool `relative_module_path`: %s", relative_module_path)
    logger.warning("ORM Pool Backends Package Path: %s" % engine_pkg_path)

    backend_type_list = [".mysql", ".postgresql", ".oracle"]

    for alias, _db in databases.items():
        engine = _db.get("ENGINE")

        if engine is None:
            raise ImproperlyConfigured("DATABASES.%s have not [ENGINE] configured!" % alias)

        for backend_type in backend_type_list:
            if backend_type in engine:
                new_engine = engine_pkg_path + backend_type
                _db["ENGINE"] = new_engine
                options = _db.get("OPTIONS", {})

                # In fact no need to autocommit
                is_necessary = False
                if is_necessary and options.get('autocommit') is None:
                    _db["OPTIONS"] = {
                        'autocommit': True,
                        **options
                    }

                break
        else:
            raise ImproperlyConfigured("DATABASES.%s.ENGINE: %s, is not supported!" % (alias, engine))


setup()
logging.warning("Database Pool New Settings: %s\n", json.dumps(settings.DATABASES, indent=4))
