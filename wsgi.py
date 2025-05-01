from web_app import init_app
import os, sys, json,traceback
from flask import Flask, request, render_template, jsonify, send_file,redirect
from werkzeug.utils import secure_filename
from web_app.controller.analyzer_controller import process_folder
from web_app.controller.json_controller import export_to_json
from web_app.model.json_for_useCase import get_json_for_useCase
import shutil
from web_app.controller.uml_controller import generate_uml
from web_app.model.user_model import login_verification
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "/")))
app = init_app()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    app.config["user_name"] = request.form.get("user_name")
    user_pwd = request.form.get("user_pwd")

    if login_verification(app.config["user_name"], user_pwd):
        upload_folder=app.config["UPLOAD_FOLDER"]
        app.config["is_login"]=True
        json_dir = f'{upload_folder}/{app.config["user_name"]}/Json_toAI'
        upload_folder = f'{upload_folder}/{app.config["user_name"]}/uploads'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        if not os.path.exists(json_dir):
            os.makedirs(json_dir, exist_ok=True)
        return render_template("main.html", user_name=app.config["user_name"])
    else:
        app.config["user_name"]=None
        app.config["is_login"] = False
        return jsonify({"success": False, "error": "Invalid username or password."}), 401


@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/reset_db", methods=["POST"])
def reset_db_route():
    db=app.config["db"]
    status = db.reset_db()
    if status:
        jsonify({"message":"Database reset successfully"}),200
    else:
        return jsonify({"error": "Fail to reset database"}), 500


@app.route("/initialize_db", methods=["POST"])
def initialize_db():
    db=app.config["db"]
    cursor=app.config["cursor"]
    try:
        db.reset_db()
        # Ensure JSON_DIR exists in the persistent disk directory
        if not os.path.exists(app.config["JSON_DIR"]):
            os.makedirs(app.config["JSON_DIR"], exist_ok=True)
        # Delete all files from Json_toAI
        for filename in os.listdir(app.config["JSON_DIR"]):
            file_path = os.path.join(app.config["JSON_DIR"], filename)
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
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

    if not (app.config["user_name"] and app.config["is_login"]):
        return redirect("/")
    
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
            full_save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_path)
            # Create directory structure if it doesn't exist.
            os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
            file.save(full_save_path)

    return jsonify({
        "message": f"✅ {len(uploaded_files)} files uploaded successfully!",
        "uploaded_path": app.config["UPLOAD_FOLDER"]
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
    errorMessages = []
    if not app.config["is_login"]:
        return redirect("/")
    
    try:
        folder_path = app.config["UPLOAD_FOLDER"]
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
        export_result,json_error= export_to_json(data, project_name, app.config["JSON_DIR"])
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
    try:
        user_name = app.config["user_name"]
        upload_folder=app.config["UPLOAD_FOLDER"]
        json_dir = f'{upload_folder}/{user_name}/Json_toAI'
        # List all files in the JSON_DIR ending with .json
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
        if not json_files:
            return jsonify({"error": "No JSON file found in Json_toAI directory."}), 404

        # Assume there is only one JSON file, so pick the first one.
        json_file = os.path.join(json_dir, json_files[0])
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_uml", methods=["POST"])
def get_uml():
    if not (app.config["user_name"] and app.config["is_login"]):
        return redirect("/")
    
    document_type = request.form.get("document_type")
    user_name = app.config["user_name"]
    upload_folder=app.config["UPLOAD_FOLDER"]
    json_dir = f'{upload_folder}/{user_name}/Json_toAI'

    return generate_uml(document_type, json_dir)

if __name__ == "__main__":
    app.run(host='0.0.0.0')