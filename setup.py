from setuptools import setup, find_packages
import os

version = '1.1.1'

setup(
    name='django-database-conn-pool',
    version=version,
    maintainer="luojidr",
    maintainer_email='luojidr@163.com',
    description="django database backend pooling for connections",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Framework :: Django :: 3",
        "Framework :: Django :: 4.0",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers"
    ],
    keywords='django connection pooling mysql postgresql cx_Oracle',
    author='luojidr',
    author_email='luojidr@163.com',
    url='https://github.com/luojidr/django-database-pool',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'django>=3.0,<=4.0.8',
        'sqlalchemy==1.4.44',
        'cx-Oracle==8.3.0',
        'psycopg2==2.9.5'
    ],
)
