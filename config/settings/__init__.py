"""Settings package helpers.

PyMySQL lets the project connect to MySQL on shared hosting/cPanel without
compiling mysqlclient. If mysqlclient is installed instead, this block is harmless.
"""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
