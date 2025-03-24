import os, sys, json, openai, re, subprocess, traceback
from urllib.parse import quote
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from controller.metaData_generation import process_folder
from controller.create_useCase_diagram import export_to_json
from model.json_for_useCase import get_json_for_useCase
from werkzeug.utils import secure_filename
from controller.ai_code_analysis import ai_code_analysis
import shutil

from web_app.controller.create_uml import generate_uml_controller
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from config.dbConfig import db_connect,reset_db,db,cursor,isDBconnected

# ✅ 設定 PlantUML JAR 檔案路徑
PLANTUML_JAR_PATH = "./PlantUML/plantuml-1.2025.1.jar"  # **確保這個路徑正確**
OUTPUT_PUML = "output.puml"
OUTPUT_PNG = "output.png"

# ✅ 設定 Flask
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ✅ 設定 Azure OpenAI
client = openai.AzureOpenAI(
    azure_endpoint="https://fyp2025.openai.azure.com",
    api_key="3kDNJlmeMVUQa1a88MWNOWnWQtb2Mdgt0J9EKKcNLubRhXngK3PiJQQJ99BBACYeBjFXJ3w3AAABACOGDCXh",
    api_version="2024-02-01"
)

# ✅ 允許的檔案類型
ALLOWED_EXTENSIONS = {"py", "js", "java", "cpp", "ts"}

# ✅ 定義合法的 component_type 和 dependency_type
VALID_COMPONENT_TYPES = {"class", "function", "module", "external_library"}
VALID_DEPENDENCY_TYPES = {"uses", "implements", "extends", "includes", "calls", "imports"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# 📌 **首頁**
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/reset_db", methods=["POST"])
def reset_db():
    global db,cursor,isDBconnected
    status=reset_db()
    if not (status or isDBconnected):
        return jsonify({"error": "無法連接 MySQL"}), 500
    elif not status:
        return jsonify({"error": f"重置失敗"}), 500


# 📌 **API: 重新建立資料表**
@app.route("/initialize_db", methods=["POST"])
def initialize_db():
    global db,cursor,isDBconnected
    if not isDBconnected:
        # Get database connection
        db, cursor = db_connect()
        if not isDBconnected:
            return jsonify({"error": "無法連接 MySQL"}), 500

    try:
        reset_db()
        # Delete all files from Json_toAI folder
        json_dir = "web_app/Json_toAI"
        if os.path.exists(json_dir):
            for filename in os.listdir(json_dir):
                file_path = os.path.join(json_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
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
        isDBconnected=False
        
@app.route("/upload", methods=["POST"])
def upload():
    uploaded_files = request.files.getlist("file")

    if not uploaded_files:
        return jsonify({"error": "No files received"}), 400

    for file in uploaded_files:
        if file and allowed_file(file.filename):
            # 👇 Preserve subfolder structure (example: "project1/main.py")
            relative_path = file.filename  # this keeps subfolders if browser supports it
            safe_path = secure_filename(relative_path.replace("\\", "/"))  # Windows fix
            full_save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_path)

            os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
            file.save(full_save_path)

    return jsonify({
        "message": f"✅ {len(uploaded_files)} files uploaded successfully!",
        "uploaded_path": app.config["UPLOAD_FOLDER"]
    }), 200
    
@app.route("/analyse_folder", methods=["POST"])
def analyse_folder():
    """
    Expects form-data with "folder_name" under UPLOAD_FOLDER.
    This endpoint:
      1. Calls process_folder() to analyze and ingest data into MySQL.
      2. Retrieves use-case data from the database.
      3. Exports metadata (JSON, GZ, TXT).
      4. Sends TXT content to the AI platform.
    """
    try:
        # 1️⃣ Get folder name and build path
        folder_name = request.form.get("folder_name")
        if not folder_name:
            return jsonify({"error": "No folder specified in the request."}), 400

        folder_path = os.path.join(app.config["UPLOAD_FOLDER"], folder_name)
        if not os.path.isdir(folder_path):
            return jsonify({"error": f"Folder '{folder_path}' does not exist."}), 404

        print(f"✅ Starting analysis on folder: {folder_path}")

        # 2️⃣ Call AI analysis pipeline (includes process_folder + export)
        from controller.ai_code_analysis import ai_code_analysis
        ai_response = ai_code_analysis(folder_path, folder_name)

        # 3️⃣ Save AI response to file
        with open("web_app/Json_toAI/ai_analysis.json", "w", encoding="utf-8") as f:
            json.dump(ai_response, f, indent=2)

        # 4️⃣ (Optional) Return AI response directly
        return jsonify({"message": "✅ Analysis complete!", "ai_response": ai_response}), 200

    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
    
# 📌 **查詢分析結果 API**
@app.route("/results", methods=["GET"])
def get_results():
    json_dir = "web_app/Json_toAI"
    try:
        # List all files in the directory ending with .json
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

@app.route("/generate_uml", methods=["POST"])
def generate_uml():
    document_type = request.form.get("document_type", "use case diagram")
    return generate_uml_controller(document_type)

@app.route("/download_uml", methods=["GET"])
def download_uml():
    uml_path = os.path.abspath(OUTPUT_PNG)  # 確保 `output.png` 的完整路徑
    if os.path.exists(uml_path):
        return send_file(uml_path, as_attachment=True, mimetype="image/png")
    return jsonify({"error": "UML diagram does not exist！"}), 404

@app.route("/download_puml", methods=["GET"])
def download_puml():
    puml_path = os.path.abspath(OUTPUT_PUML)  # 確保 `output.puml` 的完整路徑
    if os.path.exists(puml_path):
        return send_file(puml_path, as_attachment=True, mimetype="text/plain")
    return jsonify({"error": "PUML file does not exist！"}), 404

if __name__ == "__main__":
    app.run(debug=True)
