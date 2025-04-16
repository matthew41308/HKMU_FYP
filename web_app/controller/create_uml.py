import os
import subprocess
import traceback
import base64
from io import BytesIO
from flask import jsonify, current_app
from config.external_ai_config import get_prompt, get_openai

def generate_uml_controller(document_type: str, json_dir):
    try:
        # STEP 1: Generate the full prompt for AI
        prompt_template = get_prompt(document_type)
        txt_files = [f for f in os.listdir(json_dir) if f.endswith(".txt")]
        if not txt_files:
            return jsonify({"error": "No .txt file found in Json_toAI folder"}), 404

        txt_path = os.path.join(json_dir, txt_files[-1])
        with open(txt_path, "r", encoding="utf-8") as f:
            exported_text = f.read()

        full_prompt = (
            f"Please help me generate this document type: {document_type}. If it is not a technical document for project management, please respond with 0 only.\n\n"
            + prompt_template
            + exported_text
        )

        # STEP 2: Get the UML code from the AI (using OpenAI API)
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

        ai_reply = response.choices[0].message.content.strip()
        if ai_reply == "0":
            return jsonify({"error": "AI determines this is not a valid technical document"}), 400

        # Clean up the PlantUML code from the response.
        plantuml_code = ai_reply.replace("```plantuml", "").replace("```", "").strip()
        if not plantuml_code.startswith("@startuml"):
            plantuml_code = "@startuml\n" + plantuml_code + "\n@enduml"

        # STEP 3: Generate the UML diagram image in-memory using PlantUML's -pipe mode.
        # The '-pipe' flag makes PlantUML read from stdin and output the PNG to stdout.
        process = subprocess.Popen(
            ["java", "-jar", current_app.config["PLANTUML_JAR_PATH"], "-pipe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Send the PlantUML code to the process and capture the PNG output.
        png_output, error_output = process.communicate(input=plantuml_code.encode("utf-8"))

        if process.returncode != 0:
            return jsonify({"error": f"PlantUML generation failed: {error_output.decode()}"}), 500

        # Encode the PNG image to a base64 string.
        encoded_png = base64.b64encode(png_output).decode("utf-8")

        # Return a JSON response containing both the image and the PUML text.
        return jsonify({
            "png": encoded_png,
            "puml": plantuml_code
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500