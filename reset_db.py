from web_app.config.dbConfig import DB
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
if __name__ =="__main__":
    conn = DB()
    conn.reset_db()