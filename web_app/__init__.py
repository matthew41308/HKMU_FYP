from flask import Flask
import os
import sys
from config.dbConfig import DB
from config.external_ai_config import get_openai, get_prompt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
def init_app():
    app = Flask(__name__)
    app.secret_key=os.getenv("FLASK_SECRET_KEY")
    conn = DB()
    db = conn.get_db()
    cursor = conn.get_cursor()
    
    # Store the db and cursor in the app config so they can be used globally
    app.config['db'] = db
    app.config['cursor'] = cursor
    app.config["USERS_PATH"] = "/var/data/users"
    app.config["JSON_DIR"] = ""
    app.config["is_login"] = False
    app.config["user_name"] = None
    app.config["ALLOWED_EXTENSIONS"] = {"py"}
    app.config["PLANTUML_JAR_PATH"] = os.getenv("PLANTUML_JAR_PATH", "/opt/plantuml.jar")
    return app