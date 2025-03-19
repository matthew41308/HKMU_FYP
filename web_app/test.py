import openai
import json
import pymysql
import subprocess
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from config.dbConfig import db_connect,db,cursor
# 🔹 設定 Azure OpenAI
client = openai.AzureOpenAI(
    azure_endpoint="https://fyp2025.openai.azure.com",
    api_key="3kDNJlmeMVUQa1a88MWNOWnWQtb2Mdgt0J9EKKcNLubRhXngK3PiJQQJ99BBACYeBjFXJ3w3AAABACOGDCXh",
    api_version="2024-02-01"
)

# 🔹 設定 PlantUML
PLANTUML_JAR_PATH = "C:\\PlantUML\\plantuml-1.2025.1.jar"
OUTPUT_PUML = "output.puml"
OUTPUT_PNG = "output.png"

# 🔹 連接 MySQL 並獲取數據
def get_mysql_data():
    try:
        db = pymysql.connect(host="localhost", user="root", password="24295151qQ!", database="cd_insight", port=3307)
        cursor = db.cursor()

        # **查詢 components**
        cursor.execute("SELECT component_name, component_type FROM components")
        components = [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]
        if not components:
            print("⚠️ Warning: MySQL `components` 資料表為空！")

        # **查詢 dependencies**
        cursor.execute("""
            SELECT c1.component_name, c2.component_name, d.dependency_type
            FROM componentdependencies d
            JOIN components c1 ON d.source_component_id = c1.component_id
            JOIN components c2 ON d.target_component_id = c2.component_id
        """)
        dependencies = [{"source": row[0], "target": row[1], "type": row[2]} for row in cursor.fetchall()]
        if not dependencies:
            print("⚠️ Warning: MySQL `componentdependencies` 資料表為空！")

        cursor.close()
        db.close()

        if not components or not dependencies:
            raise ValueError("❌ MySQL 資料不完整，請先執行 `upload` 來存入數據！")

        return {"components": components, "dependencies": dependencies}

    except Exception as e:
        print(f"❌ MySQL 錯誤: {e}")
        return None

# 🔹 生成 **改進版** PlantUML 代碼
def generate_plantuml(uml_data):
    prompt = f"""
    Generate a well-formatted PlantUML sequence diagram with clear structure.
    - Do NOT repeat participants.
    - Show only necessary interactions.
    - Ensure the direction of dependencies is correct.
    
    JSON Data:
    {json.dumps(uml_data, indent=2)}
    """
    
    try:
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

        # **修正 PlantUML，確保正確格式**
        plantuml_code = plantuml_code.replace("```plantuml", "").replace("```", "").strip()

        with open(OUTPUT_PUML, "w", encoding="utf-8") as file:
            file.write(plantuml_code)

        print(f"✅ PlantUML 代碼已儲存至 {OUTPUT_PUML}")
        return True

    except Exception as e:
        print(f"❌ OpenAI 生成 PlantUML 失敗: {e}")
        return False

# 🔹 轉換 PlantUML 為 PNG
def convert_to_png():
    if os.path.exists(PLANTUML_JAR_PATH):
        try:
            subprocess.run(["java", "-jar", PLANTUML_JAR_PATH, OUTPUT_PUML], check=True)
            print("✅ UML 圖片已成功生成！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 生成 UML 失敗: {e}")
            return False
    else:
        print(f"❌ 找不到 PlantUML JAR 檔案: {PLANTUML_JAR_PATH}")
        return False

# 🔹 **開始測試**
uml_data = get_mysql_data()
if not uml_data:
    print("❌ 退出：未能獲取 MySQL 數據")
    exit()

print("🔍 準備送出 AI 分析...")
if generate_plantuml(uml_data):
    convert_to_png()
