from web_app.config.dbConfig import DB

if __name__ =="__main__":
    conn = DB()
    conn.reset_db()