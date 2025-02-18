
import mysql.connector
from mysql.connector import errorcode

db=None
cursor=None
config = {
  'user': 'root',
  'password': '24295151qQ!',
  'host': 'localhost',
  'port':'3307',
  'database': 'cd_insight',
  'raise_on_warnings': True,
  'auth_plugin': 'mysql_native_password'
}

def db_connect():
    global db,cursor
    try:
        if db is None or not db.is_connected():
            db=mysql.connector.connect(**config)
            cursor=db.cursor()
            print("Successfully connected to database")
        return db
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)



if __name__ == '__main__':
    db=db_connect()
    print("Database connection:", db)
    db.close()
