import pymysql
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

db = None
cursor = None
isDBconnected=False


def db_connect():
    """ 建立 MySQL 連線 """
    try:
        global db,cursor,isDBconnected
        print("🔹 嘗試使用 pymysql 連接 MySQL...")
        db = pymysql.connect(**config)
        cursor = db.cursor()
        isDBconnected=True
        print("✅ pymysql 連接 MySQL 成功！")

        return db, cursor
    except pymysql.MySQLError as e:
        print(f"❌ pymysql 連接 MySQL 失敗: {e}")
        return None, None
    
def check_connection():
    global db,isDBconnected
    """
    Check if database connection is alive
    Args:
        db: Database connection
    Returns:
        bool: True if connection is alive, False otherwise
    """
    try:
        db.ping(reconnect=True)
        isDBconnected=True
        return True
    except Exception:
        isDBconnected=False
        return False
    
def reset_db():
    global db,cursor,isDBconnected
    if not isDBconnected:
        # Get database connection
        db, cursor = db_connect()
        if not isDBconnected:
            print(f"❌ pymysql 連接 MySQL 失敗: {e}")
            return False

    try:
        # **先停用外鍵檢查**
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

        # **正確的 DROP 順序**
        cursor.execute("DELETE FROM variableparametermapping;")
        cursor.execute("DELETE FROM methodparameters;")
        cursor.execute("DELETE FROM methods;")
        cursor.execute("DELETE FROM componentdependencies;")
        cursor.execute("DELETE FROM components;")
        cursor.execute("DELETE FROM variables;")
        cursor.execute("DELETE FROM organizations;")

        # **恢復外鍵檢查**
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

        db.commit()
        print({"message": "✅ 資料庫已成功重置！"})
        return True
    
    except Exception as e:
        db.rollback()
        print({"error": f"重置失敗: {e}"})
        return False

    finally:
        cursor.close()
        db.close()
        isDBconnected=False

def get_mysql_password():

    mysql_password = os.getenv('MYSQL_PASSWORD')
    if mysql_password is None:
        raise EnvironmentError(
            "Environment variable 'MYSQL_PASSWORD' is not set. "
        )
    return mysql_password

config = {
    'host': 'mysql-6xgt',   
    'user': 'mysql',
    'password': get_mysql_password(),  
    'database': 'cd_insight',
    'port': 3306,        
    'cursorclass': pymysql.cursors.DictCursor, 
    'autocommit': True
}
    
if __name__=="__main__":
    reset_db()