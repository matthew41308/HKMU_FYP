import pymysql
from sshtunnel import SSHTunnelForwarder
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Global connection variables
db = None
cursor = None
tunnel = None
isDBconnected = False

# SSH tunnel configuration (modify these values as needed)
SSH_CONFIG = {
    'ssh_address_or_host': 'srv-cvmcbfs9c44c73ejoun0@ssh.oregon.render.com',  # SSH host address
    'ssh_port': 22,                      # SSH port, usually 22
    'ssh_username': 'root',             # SSH username
    'ssh_pkey': '/project/src/ssh/render_key'   # Path to the private key file
}

def get_mysql_password():
    mysql_password = os.getenv('MYSQL_ROOT_PASSWORD')
    if mysql_password is None:
        raise EnvironmentError(
            "Environment variable 'MYSQL_ROOT_PASSWORD' is not set. "
        )
    return mysql_password

# MySQL connection configuration (initial values; host/port will be overridden after starting the tunnel)
config = {
    'host': 'mysql-pj6a',   
    'user': 'root',
    'password': get_mysql_password(),  
    'database': 'cd_insight',
    'port': 3306,        
    'cursorclass': pymysql.cursors.DictCursor, 
    'autocommit': True
}

def db_connect():
    """Establish MySQL connection via an SSH tunnel."""
    global db, cursor, isDBconnected, tunnel
    try:
        print("🔹 Establishing SSH tunnel to MySQL server...")
        tunnel = SSHTunnelForwarder(
            (SSH_CONFIG['ssh_address_or_host'], SSH_CONFIG['ssh_port']),
            ssh_username=SSH_CONFIG['ssh_username'],
            ssh_pkey=SSH_CONFIG['ssh_pkey'],
            remote_bind_address=('127.0.0.1', 3306)
        )
        tunnel.start()
        print(f"✅ SSH tunnel established on local port: {tunnel.local_bind_port}")
        
        # Update the MySQL connection config to use the local end of the SSH tunnel.
        config_local = config.copy()
        config_local['host'] = '127.0.0.1'
        config_local['port'] = tunnel.local_bind_port
        
        print("🔹 Attempting to connect to MySQL via PyMySQL...")
        db = pymysql.connect(**config_local)
        cursor = db.cursor()
        isDBconnected = True
        print("✅ PyMySQL connected to MySQL via the SSH tunnel!")
        # Return the tunnel as well so that it can be closed when no longer needed.
        return db, cursor, tunnel
    except pymysql.MySQLError as e:
        print(f"❌ PyMySQL connection failed: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ Failed to establish SSH tunnel: {e}")
        return None, None, None

def check_connection():
    """
    Check if the database connection is alive.
    Returns:
        bool: True if connection is alive, False otherwise.
    """
    global db, isDBconnected
    try:
        db.ping(reconnect=True)
        isDBconnected = True
        return True
    except Exception:
        isDBconnected = False
        return False

def reset_db():
    global db, cursor, isDBconnected, tunnel
    if not isDBconnected:
        # Get database connection via SSH tunnel
        db, cursor, tunnel = db_connect()
        if not isDBconnected:
            print("❌ PyMySQL connection to MySQL failed")
            return False

    try:
        # Disable foreign key checks before mass deletion
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        # Delete rows in the correct order based on dependencies
        cursor.execute("DELETE FROM variableparametermapping;")
        cursor.execute("DELETE FROM methodparameters;")
        cursor.execute("DELETE FROM methods;")
        cursor.execute("DELETE FROM componentdependencies;")
        cursor.execute("DELETE FROM components;")
        cursor.execute("DELETE FROM variables;")
        cursor.execute("DELETE FROM organizations;")
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        
        db.commit()
        print({"message": "✅ Database has been reset successfully!"})
        return True
    except Exception as e:
        db.rollback()
        print({"error": f"Reset failed: {e}"})
        return False
    finally:
        # Clean up: close cursor, database and SSH tunnel
        if cursor:
            cursor.close()
        if db:
            db.close()
        if tunnel:
            tunnel.stop()
        isDBconnected = False

if __name__ == "__main__":
    db_connect()