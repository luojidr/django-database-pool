Push messages with different backends for the Django framework.
===============================================================

[![MIT License](https://img.shields.io/pypi/l/django-database-conn-pool.svg)](https://opensource.org/licenses/MIT)
[![django-database-conn-pool can be installed via wheel](https://img.shields.io/pypi/wheel/django-database-conn-pool.svg)](http://pypi.python.org/pypi/django-database-conn-pool/)
[![Supported Python versions.](https://img.shields.io/pypi/pyversions/django-database-conn-pool.svg)](http://pypi.python.org/pypi/django-database-conn-pool/)

|          |               |   
| ---------|:--------------| 
| Version  |1.1.1           | 
| Web      |               |  
| Download |<http://pypi.python.org/pypi/django-database-conn-pool>  |  
| Source   |<https://github.com/luojidr/django-database-conn-pool>   | 
| Keywords |django, database pool, MySQL, PostgreSQL, Oracle    | 


About
-----

MySQL & Oracle & PostgreSQL connection pool backends of Django, Be based on SQLAlchemy. 
Work fine in multiprocessing and multithreading django project.

Installation
------------

You can install django-database-conn-pool either via the Python Package Index
(PyPI) or from source.

To install using **pip**:

``` {.sh}
$ pip install -U django-database-conn-pool
```

and then add it to your installed apps:

``` {.python}
(1.1): INSTALLED_APPS = [
    ...,
    'database_pool',
    ...,
]

(1.2): DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'my_test',
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'USER': 'mysql_test',
        'PASSWORD': '123456',
        'POOL_OPTIONS' : {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 15,
            'RECYCLE': 60 * 60
        }
    },
    ......
}

OR

(2): DATABASES = {
    'default': {
        'ENGINE': 'database_pool.backends.mysql',
        'NAME': 'my_test',
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'USER': 'mysql_test',
        'PASSWORD': '123456',
        'POOL_OPTIONS' : {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 15,
            'RECYCLE': 60 * 60
        }
    },
    ......
}
```

### Downloading and installing from source

Download the latest version of django-database-conn-pool from
<http://pypi.python.org/pypi/django-database-conn-pool>

You can install it by doing the following,:

    $ tar xvfz django-database-pool-0.0.0.tar.gz
    $ cd django-database-pool-0.0.0
    $ python setup.py build
    # python setup.py install

The last command must be executed as a privileged user if you are not
currently using a virtualenv.
