import os, sys, json, openai, re, subprocess, traceback
from urllib.parse import quote
from flask import Flask, request, render_template, jsonify, send_file,current_app
from werkzeug.utils import secure_filename
from controller.metaData_generation import process_folder
from controller.create_useCase_diagram import export_to_json
from model.json_for_useCase import get_json_for_useCase
from controller.ai_code_analysis import ai_code_analysis
import shutil
from controller.create_uml import generate_uml_controller
from config.dbConfig import DB
from model.user_model import login_verification

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))


PLANTUML_JAR_PATH = "./PlantUML/plantuml-1.2025.1.jar"  # **確保這個路徑正確**
OUTPUT_PUML = "output.puml"
OUTPUT_PNG = "output.png"
is_login=False
user_name=None

app = Flask(__name__)
app.secret_key=os.getenv("FLASK_SECRET_KEY")

# Create folder for uploads on the persistent disk
USERS_FOLDER="/var/data/users"
UPLOAD_FOLDER=""

# Create Json_toAI folder on the persistent disk
JSON_DIR = ""


client = openai.AzureOpenAI(
    azure_endpoint="https://fyp2025.openai.azure.com",
    api_key="3kDNJlmeMVUQa1a88MWNOWnWQtb2Mdgt0J9EKKcNLubRhXngK3PiJQQJ99BBACYeBjFXJ3w3AAABACOGDCXh",
    api_version="2024-02-01"
)


ALLOWED_EXTENSIONS = {"py"}


VALID_COMPONENT_TYPES = {"class", "function", "module", "external_library"}
VALID_DEPENDENCY_TYPES = {"uses", "implements", "extends", "includes", "calls", "imports"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Create the database connection once before the first request
@app.before_first_request
def init_db_connection():
    conn = DB()
    db = conn.get_db()
    cursor = conn.get_cursor()
    isDBconnected=conn.is_db_connected()
    if not isDBconnected:
        raise Exception("Failed to establish database connection")
    # Store the db and cursor in the app config so they can be used globally
    app.config['db'] = db
    app.config['cursor'] = cursor
    print("Database connection established.")

# Close the database connection when the application context ends
@app.teardown_appcontext
def close_db_connection(exception):
    db = current_app.config.get('db')
    if db is not None:
        db.close()
        print("Database connection closed.")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    global user_name,UPLOAD_FOLDER,USERS_FOLDER,JSON_DIR,app,is_login
    user_name = request.form.get("user_name")
    user_pwd = request.form.get("user_pwd")

    if login_verification(user_name, user_pwd):
        is_login=True
        UPLOAD_FOLDER = f"{USERS_FOLDER}/{user_name}/uploads"
        # Create Json_toAI folder on the persistent disk
        JSON_DIR = f"{USERS_FOLDER}/{user_name}/Json_toAI"
        app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
        app.config["JSON_DIR"]=JSON_DIR
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        if not os.path.exists(JSON_DIR):
            os.makedirs(JSON_DIR, exist_ok=True)
        return render_template("main.html", user_name=user_name)
    else:
        user_name=None
        is_login=False
        return jsonify({"success": False, "error": "Invalid username or password."}), 401


@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/reset_db", methods=["POST"])
def reset_db_route():
    db=current_app.config["db"]
    status = db.reset_db()
    if status:
        jsonify({"message":"Database reset successfully"}),200
    else:
        return jsonify({"error": "Fail to reset database"}), 500


@app.route("/initialize_db", methods=["POST"])
def initialize_db():
    db=current_app.config["db"]
    cursor=current_app.config["cursor"]
    try:
        db.reset_db()
        # Ensure JSON_DIR exists in the persistent disk directory
        if not os.path.exists(JSON_DIR):
            os.makedirs(JSON_DIR, exist_ok=True)
        # Delete all files from Json_toAI
        for filename in os.listdir(JSON_DIR):
            file_path = os.path.join(JSON_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as del_exc:
                print(f"Failed to delete {file_path}. Reason: {del_exc}")
        return jsonify({"message": "✅ All data tables have been created!"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"❌ Failed to create table: {str(e)}"}), 500

    finally:
        cursor.close()
        db.close()

@app.route("/upload", methods=["POST"])
def upload():
    global is_login, user_name  # make sure these globals are defined elsewhere
    if not (user_name and is_login):
        return render_template("index.html")
    
    uploaded_files = request.files.getlist("file")
    if not uploaded_files:
        return jsonify({"error": "No files received"}), 400

    for file in uploaded_files:
        if file and allowed_file(file.filename):
            # Use webkitRelativePath if it exists for preserving folder structure.
            relative_path = (
                file.webkitRelativePath
                if hasattr(file, "webkitRelativePath") and file.webkitRelativePath
                else file.filename
            )
            # Standardize the path delimiters to forward slash.
            relative_path = relative_path.replace("\\", "/")
            # Split the path into its components, then secure each part.
            parts = [secure_filename(part) for part in relative_path.split("/") if part]
            # Reconstruct the path preserving the directory structure.
            safe_path = os.path.join(*parts)
            full_save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_path)
            # Create directory structure if it doesn't exist.
            os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
            file.save(full_save_path)

    return jsonify({
        "message": f"✅ {len(uploaded_files)} files uploaded successfully!",
        "uploaded_path": current_app.config["UPLOAD_FOLDER"]
    }), 200

@app.route("/analyse_folder", methods=["POST"])
def analyse_folder():
    """
    This endpoint:
      1. Processes the folder (analyzes files/folders and ingests data into MySQL).
      2. Retrieves use-case data from the database.
      3. Exports metadata (JSON, GZ, TXT).
      4. Returns all error messages (if any) along with a success status.
    """
    global is_login
    errorMessages = []
    if not is_login:
        return render_template("index.html")
    
    try:
        folder_path = current_app.config["UPLOAD_FOLDER"]
        if not os.path.isdir(folder_path):
            return jsonify({"error": f"Folder '{folder_path}' does not exist."}), 404
        
        print(f"✅ Starting analysis on folder: {folder_path}")
        project_name = request.form.get("projectName")

        # STEP 1: Process the folder and capture any error messages.
        folder_errors = process_folder(folder_path)
        if folder_errors:
            errorMessages.extend(folder_errors)
        else:
            print("✅ Folder processing completed with no errors.")
        
        # STEP 2: Retrieve use-case data from the database.
        data,data_error = get_json_for_useCase()
        if data_error:
            errorMessages.append(data_error)
            return jsonify({
                "message": "Operation completed with some errors.",
                "error": errorMessages
            }), 500
        else:
            print("✅ Use-case data successfully retrieved.")
        
        # STEP 3: Export the use-case data to JSON, GZ, and TXT files.
        export_result,json_error= export_to_json(data, project_name, current_app.config["JSON_DIR"])
        if json_error:
            errorMessages.append(json_error)
            return jsonify({
                "message": "Operation completed with some errors.",
                "error": errorMessages
            }), 500
        else:
            print(f"✅ Data exported successfully to file: {export_result}")
        
        # Combine and return all error messages if any.
        if errorMessages:
            return jsonify({
                "message": "Operation completed but some errors occur when analyzing folders. It may affect the result of diagrams",
                "error": errorMessages
            }), 500
        else:
            return jsonify({"message": "✅ Analysis complete!"}), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500



@app.route("/results", methods=["GET"])
def get_results():
    global JSON_DIR
    try:
        # List all files in the JSON_DIR ending with .json
        json_files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]
        if not json_files:
            return jsonify({"error": "No JSON file found in Json_toAI directory."}), 404

        # Assume there is only one JSON file, so pick the first one.
        json_file = os.path.join(JSON_DIR, json_files[0])
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_uml", methods=["POST"])
def generate_uml():
    global user_name,is_login,JSON_DIR
    if not (user_name and is_login) :
        return render_template("index.html")

    document_type = request.form.get("document_type")
    return generate_uml_controller(document_type,JSON_DIR)

@app.route("/download_uml", methods=["GET"])
def download_uml():
    uml_path = os.path.abspath(OUTPUT_PNG)
    if os.path.exists(uml_path):
        return send_file(uml_path, as_attachment=True, mimetype="image/png")
    return jsonify({"error": "UML diagram does not exist！"}), 404

@app.route("/download_puml", methods=["GET"])
def download_puml():
    puml_path = os.path.abspath(OUTPUT_PUML)
    if os.path.exists(puml_path):
        return send_file(puml_path, as_attachment=True, mimetype="text/plain")
    return jsonify({"error": "PUML file does not exist！"}), 404


if __name__ == "__main__":
    current_app.run(debug=True)