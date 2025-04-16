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
    isDBconnected=conn.is_db_connected()
    if not isDBconnected:
        raise Exception("Failed to establish database connection")
    # Store the db and cursor in the app config so they can be used globally
    app.config['db'] = db
    app.config['cursor'] = cursor
    app.config["UPLOAD_FOLDER"] = "/var/data/users"
    app.config["JSON_DIR"] = ""
    app.config["PLANTUML_JAR_PATH"]="./PlantUML/plantuml-1.2025.1.jar"
    app.config["OUTPUT_PUML"] = "output.puml"
    app.config["OUTPUT_PNG"] = "output.png"
    app.config["is_login"] = False
    app.config["user_name"] = None
    app.config["ALLOWED_EXTENSIONS"] = {"py"}
    return app