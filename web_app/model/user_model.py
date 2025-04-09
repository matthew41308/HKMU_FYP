import pymysql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from config.dbConfig import db_connect,db,cursor,isDBconnected

def login_verification(user_name, user_pwd):
    if(user_name == None or user_pwd == None):
        return False
    
    sql="""
        SELECT user_name, user_pwd from users
        WHERE user_name = %s
        """
    cursor.execute(sql,(user_name))
    result = cursor.fetchone()
    returned_user_pwd = result['user_pwd'] if result else None
    if returned_user_pwd == None or returned_user_pwd!=user_pwd:
        return False
    
    return True
