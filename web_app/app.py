import os, sys, json, openai, re, subprocess, traceback
from urllib.parse import quote
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from config.dbConfig import db_connect,reset_db,db,cursor,isDBconnected

# ✅ 設定 PlantUML JAR 檔案路徑
PLANTUML_JAR_PATH = "C:\\PlantUML\\plantuml-1.2025.1.jar"  # **確保這個路徑正確**
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
        # 🔹 建立 `components` 表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS components (
            component_id INT AUTO_INCREMENT PRIMARY KEY,
            component_name VARCHAR(255) NOT NULL,
            component_type ENUM('class', 'function', 'module', 'external_library') NOT NULL,
            description TEXT
        );
        """)

        # 🔹 建立 `methods` 表 (與 components 有外鍵關係)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS methods (
            method_id INT AUTO_INCREMENT PRIMARY KEY,
            component_id INT NOT NULL,
            method_name VARCHAR(255) NOT NULL,
            FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE
        );
        """)

        # 🔹 建立 `methodparameters` 表 (與 methods 有外鍵關係)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS methodparameters (
            parameter_id INT AUTO_INCREMENT PRIMARY KEY,
            method_id INT NOT NULL,
            parameter_name VARCHAR(255) NOT NULL,
            parameter_type VARCHAR(255),
            FOREIGN KEY (method_id) REFERENCES methods(method_id) ON DELETE CASCADE
        );
        """)

        # 🔹 建立 `variableparametermapping` 表 (與 methodparameters 有外鍵關係)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS variableparametermapping (
            mapping_id INT AUTO_INCREMENT PRIMARY KEY,
            parameter_id INT NOT NULL,
            variable_name VARCHAR(255) NOT NULL,
            FOREIGN KEY (parameter_id) REFERENCES methodparameters(parameter_id) ON DELETE CASCADE
        );
        """)

        # 🔹 建立 `componentdependencies` 表 (與 components 有外鍵關係)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS componentdependencies (
            source_component_id INT NOT NULL,
            target_component_id INT NOT NULL,
            dependency_type ENUM('uses', 'calls', 'imports', 'extends') NOT NULL,
            PRIMARY KEY (source_component_id, target_component_id),
            FOREIGN KEY (source_component_id) REFERENCES components(component_id) ON DELETE CASCADE,
            FOREIGN KEY (target_component_id) REFERENCES components(component_id) ON DELETE CASCADE
        );
        """)

        db.commit()
        return jsonify({"message": "✅ All data tables have been created!"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"❌ Failed to create table: {str(e)}"}), 500

    finally:
        cursor.close()
        db.close()
        isDBconnected=False
        
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # ✅ 儲存檔案
    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(file_path)
    print(f"✅ File {file.filename} saved to {file_path}")  # 🔹 Debug 訊息

    # ✅ 讀取程式碼並發送至 AI 進行分析
    with open(file_path, "r") as f:
        code_content = f.read()
    
    print("🔍 Submit code for AI analysis...")  # 🔹 Debug 訊息
    analysis_result = ai_code_analysis(code_content)
    
    if "error" in analysis_result:
        print(f"❌ AI analysis fails: {analysis_result['error']}")  # 🔹 Debug 訊息
        return jsonify({"error": analysis_result["error"]}), 500

    print("✅ AI 分析完成，準備儲存到 MySQL...")  # 🔹 Debug 訊息

    # ✅ 連接 MySQL
    global db,cursor,isDBconnected
    if not isDBconnected:
        # Get database connection
        db, cursor = db_connect()
        if not isDBconnected:
            return jsonify({"error": "無法連接 MySQL"}), 500

    try:
        # ✅ 儲存 `components`
        query_component = "INSERT INTO components (component_name, component_type, description) VALUES (%s, %s, %s)"
        component_ids = {}

        for component in analysis_result["components"]:
            component_type = component["component_type"]

            # ✅ 確保 component_type 只有合法值
            if component_type not in VALID_COMPONENT_TYPES:
                component_type = "external_library"

            cursor.execute(query_component, (component["component_name"], component_type, component["description"]))
            component_ids[component["component_name"]] = cursor.lastrowid

        print("📥 All components have been successfully stored in MySQL")  # 🔹 Debug 訊息

        # ✅ 儲存 `dependencies`
        query_dependency = "INSERT INTO componentdependencies (source_component_id, target_component_id, dependency_type) VALUES (%s, %s, %s)"
        for dependency in analysis_result["dependencies"]:
            source_id = component_ids.get(dependency["source_component"])
            target_id = component_ids.get(dependency["target_component"])
            dependency_type = dependency["dependency_type"]

    # ✅ 修正 `dependency_type`，確保符合 MySQL ENUM 值
        '''if dependency_type not in VALID_DEPENDENCY_TYPES:
            print(f"⚠️ Invalid dependency_type: {dependency_type}, defaulting to 'uses'")
            dependency_type = "uses" # 👉 Defaults back to `uses` to avoid MySQL storage errors'''
        print("📥 Stored dependencies:", json.dumps(dependency, indent=2))

        if source_id and target_id:
            cursor.execute(query_dependency, (source_id, target_id, dependency_type))

        db.commit()  # 🔹 提交變更
        print("✅ MySQL deposit successful!")  # 🔹 Debug 訊息

        return jsonify({"message": f"✅ The file {file.filename} has been uploaded successfully, analyzed and saved in the database!"}), 200

    except Exception as e:
        db.rollback()
        print(f"❌ Storage failed: {e}")  # 🔹 Debug 訊息
        return jsonify({"error": f"Storage failed: {e}"}), 500

    finally:
        cursor.close()
        db.close()
        isDBconnected=False
        

# 📌 **查詢分析結果 API**
@app.route("/results", methods=["GET"])
def get_results():
    global db,cursor,isDBconnected
    if not isDBconnected:
        # Get database connection
        db, cursor = db_connect()
        if not isDBconnected:
            return jsonify({"error": "無法連接 MySQL"}), 500

    try:
        # ✅ 查詢 `components` 和 `methods`
        cursor.execute("""
        SELECT c.component_name, c.component_type, c.description, 
               COALESCE(GROUP_CONCAT(m.method_name SEPARATOR ', '), '') AS methods
        FROM components c
        LEFT JOIN methods m ON c.component_id = m.component_id
        GROUP BY c.component_id
        ORDER BY c.component_id DESC LIMIT 5;
        """)
        components_results = cursor.fetchall()

        # ✅ 查詢 `componentdependencies`
        cursor.execute("""
        SELECT source_component_id, target_component_id, dependency_type
        FROM componentdependencies
        ORDER BY source_component_id DESC LIMIT 5;
        """)
        dependencies_results = cursor.fetchall()

        return jsonify({
            "components": components_results,
            "dependencies": dependencies_results
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()
        isDBconnected=False

# 📌 **生成 UML API**
@app.route("/generate_uml", methods=["GET"])
@app.route("/generate_uml", methods=["GET"])
def generate_uml():
    global db,cursor,isDBconnected
    if not isDBconnected:
        # Get database connection
        db, cursor = db_connect()
        if not isDBconnected:
            return jsonify({"error": "無法連接 MySQL"}), 500

    try:
        # 🔹 查詢 components
        cursor.execute("SELECT component_name, component_type FROM components")
        results = cursor.fetchall()
        components = [{"name": row["component_name"], "type": row["component_type"]} for row in results]

        if not components:
            print("⚠️ MySQL `components` table is empty！")
            return jsonify({"error": "❌ No components found, please check if there is data in the database"}), 500

        # 🔹 查詢 dependencies
        cursor.execute("""
            SELECT c1.component_name AS source_component, 
                c2.component_name AS target_component, 
                d.dependency_type
            FROM componentdependencies d
            JOIN components c1 ON d.source_component_id = c1.component_id
            JOIN components c2 ON d.target_component_id = c2.component_id
        """)
        dependencies = [{"source": row["source_component"], "target": row["target_component"], "type": row["dependency_type"]} for row in cursor.fetchall()]

        if not dependencies:
            print("⚠️ MySQL `componentdependencies` table is empty！")
            return jsonify({"error": "❌ Dependencies not found, please confirm whether there is data in the database"}), 500

        # ✅ 準備 JSON 給 AI
        uml_data = {"components": components, "dependencies": dependencies}
        print("🔍 Prepare to send AI analysis, JSON data is as follows:")
        print(json.dumps(uml_data, indent=2))  # 🛠 Debug 訊息

        # 🔹 **發送請求給 OpenAI**
        prompt = f"""
        Generate a well-formatted PlantUML sequence diagram with clear structure.
        - Do NOT repeat participants.
        - Show only necessary interactions.
        - Ensure the direction of dependencies is correct.

        JSON Data:
        {json.dumps(uml_data, indent=2)}
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

        # **修正 PlantUML，確保正確格式**
        plantuml_code = plantuml_code.replace("```plantuml", "").replace("```", "").strip()

        # **確保包含 @startuml**
        if not plantuml_code.startswith("@startuml"):
            plantuml_code = "@startuml\n" + plantuml_code + "\n@enduml"

        # 🔹 **儲存為 `output.puml`**
        with open(OUTPUT_PUML, "w", encoding="utf-8") as file:
            file.write(plantuml_code)

        print(f"✅ PlantUML code has been saved to {OUTPUT_PUML}")

        # 🔹 **執行 PlantUML 轉換 PNG**
        if os.path.exists(PLANTUML_JAR_PATH):
            subprocess.run(["java", "-jar", PLANTUML_JAR_PATH, OUTPUT_PUML], check=True)
            print("✅ UML picture generated successfully！")
        else:
            return jsonify({"error": f"PlantUML JAR file not found: {PLANTUML_JAR_PATH}"}), 500

        # **✅ 確保 `output.png` 存在後再回傳**
        output_png_path = os.path.abspath(OUTPUT_PNG)
        if os.path.exists(output_png_path):
            print(f"✅ PNG generated successfully！({output_png_path})")
            return send_file(output_png_path, mimetype="image/png")
        else:
            return jsonify({"error": "❌ output.png not generated!"}), 500

    except Exception as e:
        print("❌ Error generating UML! The detailed errors are as follows:")
        traceback.print_exc()  # ✅ 顯示完整錯誤訊息
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

    finally:
        cursor.close()
        db.close()
        isDBconnected=False

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
