import os
import sys
import pymysql
from sshtunnel import SSHTunnelForwarder

# Adjust sys.path if necessary
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
        if (self.__class__._is_db_connected and 
            self.__class__._db is not None and 
            self.__class__._cursor is not None):
            return self.__class__._db, self.__class__._cursor

        try:
            print("🔹 Establishing SSH tunnel to MySQL server...")
            # Create and start the SSH tunnel
            ssh_key = self.get_ssh_key_path()
            self.__class__._tunnel = SSHTunnelForwarder(
                ('ssh.oregon.render.com', 22),
                ssh_username='srv-cvmcbfs9c44c73ejoun0',
                ssh_pkey=ssh_key,
                remote_bind_address=('127.0.0.1', 3306)
            )
            self.__class__._tunnel.start()
            print(f"✅ SSH tunnel established on local port: {self.__class__._tunnel.local_bind_port}")

            # Prepare MySQL connection configuration using the tunnel's local port
            config_local = {
                'host': '127.0.0.1',
                'port': self.__class__._tunnel.local_bind_port,
                'user': self.get_mysql_user(),
                'password': self.get_mysql_password(),
                'database': 'cd_insight',
                'cursorclass': pymysql.cursors.DictCursor,
                'autocommit': True
            }

            print("🔹 Attempting to connect to MySQL via PyMySQL...")
            self.__class__._db = pymysql.connect(**config_local)
            self.__class__._cursor = self.__class__._db.cursor()
            self.__class__._is_db_connected = True
            print("✅ PyMySQL connected to MySQL via the SSH tunnel!")
            return self.__class__._db, self.__class__._cursor
        except pymysql.MySQLError as e:
            print(f"❌ PyMySQL connection failed: {e}")
            self.__class__._is_db_connected = False
            return None, None
        except Exception as e:
            print(f"❌ Failed to establish SSH tunnel: {e}")
            self.__class__._is_db_connected = False
            return None, None

    def check_connection(self):
        """
        Check if the database connection is alive.
        
        Returns:
            bool: True if connection is alive, False otherwise.
        """
        try:
            if self.__class__._db is not None:
                self.__class__._db.ping(reconnect=True)
            self.__class__._is_db_connected = True
        except Exception:
            self.__class__._is_db_connected = False
        return self.__class__._is_db_connected

    def close_db(self):
        """
        Close the database connection and the SSH tunnel.
        """
        if self.__class__._cursor:
            self.__class__._cursor.close()
        if self.__class__._db:
            self.__class__._db.close()
        if self.__class__._tunnel:
            self.__class__._tunnel.stop()
        self.__class__._is_db_connected = False

    def reset_db(self):
        """
        Reset the database tables by truncating them.
        Uses the shared connection.
        
        Returns:
            bool: True if reset succeeded, False otherwise.
        """
        if not self.__class__._is_db_connected:
            self.db_connect()
            if not self.__class__._is_db_connected:
                print("❌ PyMySQL connection to MySQL failed")
                return False

        try:
            self.__class__._cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            self.__class__._cursor.execute("TRUNCATE TABLE methodparameters;")
            self.__class__._cursor.execute("TRUNCATE TABLE methods;")
            self.__class__._cursor.execute("TRUNCATE TABLE components;")
            self.__class__._cursor.execute("TRUNCATE TABLE variables;")
            self.__class__._cursor.execute("TRUNCATE TABLE organizations;")
            self.__class__._cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            self.__class__._db.commit()
            print({"message": "✅ Database has been reset successfully!"})
            return True
        except Exception as e:
            self.__class__._db.rollback()
            print({"error": f"Reset failed: {e}"})
            return False
        finally:
            # Clean up resources after reset
            self.close_db()

    def get_db(self):
        """
        Returns the currently established database connection,
        or establishes a new one if needed.
        """
        if self.__class__._db is None or not self.__class__._is_db_connected:
            self.db_connect()
        return self.__class__._db

    def get_cursor(self):
        """
        Returns the currently established database cursor,
        or establishes a new connection if needed.
        """
        if self.__class__._cursor is None or not self.__class__._is_db_connected:
            self.db_connect()
        return self.__class__._cursor

    def is_db_connected(self):
        """
        Check and return the current connection status.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self.__class__._is_db_connected


if __name__ == "__main__":
    connector = DB()
    connector.db_connect()