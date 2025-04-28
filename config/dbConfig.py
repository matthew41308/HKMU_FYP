import os
import sys
import pymysql
from sshtunnel import SSHTunnelForwarder

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
class DB:
    _db = None
    _cursor = None
    _tunnel = None
    _is_db_connected = False

    @classmethod
    def get_mysql_password(cls):
        mysql_password = os.getenv('MYSQL_PASSWORD')
        if mysql_password is None:
            raise EnvironmentError("Environment variable 'MYSQL_PASSWORD' is not set.")
        return mysql_password

    @classmethod
    def get_mysql_user(cls):
        mysql_user = os.getenv('MYSQL_USER')
        if mysql_user is None:
            raise EnvironmentError("Environment variable 'MYSQL_USER' is not set.")
        return mysql_user

    @classmethod
    def get_ssh_key_path(cls):
        """
        Verify that the SSH key file exists and return its path.
        """
        key_path = '/etc/secrets/ssh_key'
        if not os.path.isfile(key_path):
            raise FileNotFoundError(f"SSH key file not found: {key_path}")
        return key_path

    def db_connect(self):
        """
        Establish a connection to MySQL via an SSH tunnel.
        If a connection is already established, return the existing connection.
        """
        # Check if connection is already established
        if self._is_db_connected:
            return self._db, self._cursor

        config = {
            "host": "127.0.0.1",
            "port": int(os.getenv("SSH_MYSQL_HOST_PORT", "3306")),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": "cd_insight",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": True,
        }
        try:
            print("🔹 Connecting to MySQL through pre-opened tunnel …")
            self._db = pymysql.connect(**config)
            self._cursor = self._db.cursor()
            print("✅ Connected!")
        except pymysql.MySQLError as e:
            print(f"❌ MySQL connection failed: {e}")
            self._db = self._cursor = None

        return self._db, self._cursor

    def close_db(self):
        """
        Close the database connection.
        """
        if self._cursor:
            self._cursor.close()
        if self._db:
            self._db.close()
        self._is_db_connected = False

    def reset_db(self):
        """
        Reset the database tables by truncating them.
        Uses the shared connection.
        
        Returns:
            bool: True if reset succeeded, False otherwise.
        """
        if not self._is_db_connected:
            self.db_connect()

        try:
            self._cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            self._cursor.execute("TRUNCATE TABLE methodparameters;")
            self._cursor.execute("TRUNCATE TABLE methods;")
            self._cursor.execute("TRUNCATE TABLE components;")
            self._cursor.execute("TRUNCATE TABLE variables;")
            self._cursor.execute("TRUNCATE TABLE organizations;")
            self._cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            self._db.commit()
            print({"message": "✅ Database has been reset successfully!"})
            return True
        except Exception as e:
            self._db.rollback()
            print({"error": f"Reset failed: {e}"})
            return False
        finally:
            # Clean up resources after reset
            self.close_db()

    def get_db(self):
        if not self._is_db_connected:
            self.db_connect()
        return self._db

    def get_cursor(self):
        if not self._is_db_connected:
            self.db_connect()
        return self._cursor

    def is_db_connected(self):
        return self._is_db_connected


if __name__ == "__main__":
    connector = DB()
    connector.db_connect()