# Config/dbConfig.py
import mysql.connector
from mysql.connector import errorcode

db = None
cursor = None
config = {
    'user': 'root',
    'password': '24295151qQ!',
    'host': 'localhost',
    'port': '3307',
    'database': 'cd_insight',
    'raise_on_warnings': True,
    'auth_plugin': 'mysql_native_password'
}

def db_connect():
    try:
        db = mysql.connector.connect(**config)
        cursor = db.cursor(buffered=True)
        print("Successfully connected to database")
        return db, cursor
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None, None



if __name__ == '__main__':
    db,cursor=db_connect()
    db.close()
