import os, sys, json, openai, re, subprocess, traceback
from urllib.parse import quote
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from controller.metaData_generation import process_folder
from controller.create_useCase_diagram import export_to_json
from model.json_for_useCase import get_json_for_useCase
from werkzeug.utils import secure_filename
import shutil
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

# ✅ AI 進行程式碼分析
def ai_code_analysis(code: str) -> dict:
    prompt = f"""
    Analyze the following code and output ONLY valid JSON with:
    {{
        "components": [
            {{
                "component_name": "ClassName or ComponentName",
                "component_type": "class/component/function/module",
                "description": "Brief description",
                "attributes": ["attribute1", "attribute2"],
                "methods": ["method1", "method2"]
            }}
        ],
        "dependencies": [
            {{
                "source_component": "ComponentA",
                "target_component": "ComponentB",
                "dependency_type": "calls/imports/extends/uses"
            }}
        ]
    }}
    Code:
    {code}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a code analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4096
        )

        # ✅ 清理 AI 回應並轉換成 JSON
        ai_output = response.choices[0].message.content.strip()
        cleaned_output = ai_output.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_output)

    except Exception as e:
        return {"error": str(e)}

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
        
    
@app.route("/analyse_folder", methods=["POST"])
def analyse_folder():
    """
    Expects a form-data field "folder" which is the name of a folder under the UPLOAD_FOLDER.
    This endpoint:
      1. Calls process_folder() to analyze and ingest folder data into MySQL.
      2. Retrieves the use-case data from the database.
      3. Exports the data (JSON, JSON.gz, and text) using export_to_json().
      4. Reads the generated text file and submits its content to the AI platform.
    """
    try:
        # Get folder name from request form.
        folder_name = request.form.get("folder_name")
        folder_path = request.form.get("folder_path")
        if not folder_path:
            return jsonify({"error": "No folder path provided."}), 400
        
        if not folder_name:
            return jsonify({"error": "No folder specified in the request."}), 400

        # Build full folder path (the folder should be present under UPLOAD_FOLDER)
        
        #if not os.path.isdir(folder_path):
        #    return jsonify({"error": f"Folder '{folder_path}' does not exist."}), 404
        
        print(f"✅ Starting analysis on folder: {folder_path}")
        # Analyze the folder and insert data into the database.
        process_folder(folder_path)

        # Ensure you have a DB connection to fetch the use-case JSON.
        global db, cursor, isDBconnected
        if not isDBconnected:
            db, cursor = db_connect()
            if cursor is None:
                return jsonify({"error": "Unable to connect to MySQL."}), 500

        # Get all data from the database (use-case data).
        data = get_json_for_useCase(db, cursor)

        # Export the data to JSON files (json, json.gz, and text) under web_app/Json_toAI.
        # Here we use the folder name as the project name.
        exported_json = export_to_json(data, folder_name)

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

@app.route("/generate_uml", methods=["GET"])
def generate_uml():
    try:
        # -----------------------------------------------------------------------------
        # Retrieve the exported txt file from the Json_toAI folder.
        # -----------------------------------------------------------------------------
        json_dir = "web_app/Json_toAI"
        txt_files = [f for f in os.listdir(json_dir) if f.endswith(".txt")]
        if not txt_files:
            return jsonify({"error": "No txt file found in Json_toAI directory."}), 404

        txt_file_path = os.path.join(json_dir, txt_files[0])
        with open(txt_file_path, "r", encoding="utf-8") as file:
            exported_text = file.read()

        print("Exported text file content:")
        print(exported_text)

        # -----------------------------------------------------------------------------
        # Build the PlantUML prompt using the content from the txt file.
        # -----------------------------------------------------------------------------
        prompt = f"""
        From the given file, the data inside are metadata extracted from a project, the data includes information of the actual code. From the relationship of the data, please try to draw a use case diagram to illustrate the design of the project, the graph should be in format of plantuml with a older version.
        Please only send me back the PlantUML code without any other response or comment
        Data:
        {exported_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in generating optimized PlantUML diagrams."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4096
        )

        plantuml_code = response.choices[0].message.content.strip()
        print("🔍 UML code for AI response:")
        print(plantuml_code)

        # -----------------------------------------------------------------------------
        # Fix PlantUML formatting: remove any markdown code block markers
        # and ensure it starts with @startuml.
        # -----------------------------------------------------------------------------
        plantuml_code = plantuml_code.replace("```plantuml", "").replace("```", "").strip()
        if not plantuml_code.startswith("@startuml"):
            plantuml_code = "@startuml\n" + plantuml_code + "\n@enduml"

        # Save the generated PlantUML code.
        with open(OUTPUT_PUML, "w", encoding="utf-8") as file:
            file.write(plantuml_code)
        print(f"✅ PlantUML code has been saved to {OUTPUT_PUML}")

        # -----------------------------------------------------------------------------
        # Execute PlantUML to convert the PUML to a PNG image.
        # -----------------------------------------------------------------------------
        if os.path.exists(PLANTUML_JAR_PATH):
            subprocess.run(["java", "-jar", PLANTUML_JAR_PATH, OUTPUT_PUML], check=True)
            print("✅ UML picture generated successfully！")
        else:
            return jsonify({"error": f"PlantUML JAR file not found: {PLANTUML_JAR_PATH}"}), 500

        # Ensure the output image exists and return it.
        output_png_path = os.path.abspath(OUTPUT_PNG)
        if os.path.exists(output_png_path):
            print(f"✅ PNG generated successfully！({output_png_path})")
            return send_file(output_png_path, mimetype="image/png")
        else:
            return jsonify({"error": "❌ output.png not generated!"}), 500

    except Exception as e:
        print("❌ Error generating UML! The detailed errors are as follows:")
        traceback.print_exc()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

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
