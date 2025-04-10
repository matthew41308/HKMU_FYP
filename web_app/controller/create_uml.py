import os
import subprocess
import traceback
from flask import send_file, jsonify
from config.external_ai_config import get_prompt, get_openai

PLANTUML_JAR_PATH = "./PlantUML/plantuml-1.2025.1.jar"
OUTPUT_PUML = "output.puml"
OUTPUT_PNG = "output.png"

def generate_uml_controller(document_type: str):
    try:
        prompt_template = get_prompt(document_type)

        json_dir = "/var/data/Json_toAI"
        txt_files = [f for f in os.listdir(json_dir) if f.endswith(".txt")]
        if not txt_files:
            return jsonify({"error": "No .txt file found in Json_toAI folder"}), 404

        txt_path = os.path.join(json_dir, txt_files[-1])
        with open(txt_path, "r", encoding="utf-8") as f:
            exported_text = f.read()

        full_prompt = prompt_template + exported_text

        client = get_openai()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in generating optimized PlantUML diagrams."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0,
            max_tokens=4096
        )

        plantuml_code = response.choices[0].message.content.strip()
        if plantuml_code.strip() == "0":
            return jsonify({"error": "AI determines that this file is not a valid technical document and cannot generate UML"}), 400
        plantuml_code = plantuml_code.replace("```plantuml", "").replace("```", "").strip()
        if not plantuml_code.startswith("@startuml"):
            plantuml_code = "@startuml\n" + plantuml_code + "\n@enduml"

        with open(OUTPUT_PUML, "w", encoding="utf-8") as f:
            f.write(plantuml_code)

        if os.path.exists(PLANTUML_JAR_PATH):
            subprocess.run(["java", "-jar", PLANTUML_JAR_PATH, OUTPUT_PUML], check=True)
        else:
            return jsonify({"error": f"PlantUML JAR not found: {PLANTUML_JAR_PATH}"}), 500

        if os.path.exists(OUTPUT_PNG):
            return send_file(OUTPUT_PNG, mimetype="image/png")
        else:
            return jsonify({"error": "UML PNG not generated!"}), 500

    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
