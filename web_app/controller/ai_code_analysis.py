from http import client
import os
import json
import traceback
from datetime import datetime
from controller.metaData_generation import process_folder
from controller.create_useCase_diagram import export_to_json
from model.json_for_useCase import get_json_for_useCase
from config.dbConfig import db_connect, db, cursor, isDBconnected
from openai import AzureOpenAI

def ai_code_analysis(folder_path: str, project_name: str) -> dict:
    try:
        # Step 1: Process the folder to populate metadata
        process_folder(folder_path)

        # Step 2: Get metadata from database
        global db, cursor, isDBconnected
        if not isDBconnected:
            db, cursor = db_connect()
            if cursor is None:
                return {"error": "❌ Failed to connect to database."}

        data = get_json_for_useCase(db, cursor)

        # Step 3: Export metadata to JSON + TXT
        export_to_json(data, project_name)

        # Step 4: Find the latest .txt file for this project
        txt_dir = "/var/data/Json_toAI"
        txt_files = [
            f for f in os.listdir(txt_dir)
            if f.startswith(project_name) and f.endswith(".txt")
        ]
        if not txt_files:
            return {"error": "❌ No exported .txt file found."}

        latest_txt = max(txt_files, key=lambda x: os.path.getmtime(os.path.join(txt_dir, x)))
        txt_path = os.path.join(txt_dir, latest_txt)

        with open(txt_path, "r", encoding="utf-8") as f:
            exported_text = f.read()
        prompt = f"""
        Analyze the following code metadata and return ONLY JSON structured as:
        {{
        "components": [
            {{
            "component_name": "Name",
            "component_type": "class/function/module",
            "description": "Brief description",
            "attributes": [],
            "methods": []
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
        Data:
        {exported_text}
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a code analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4096
        )
        ai_output = response.choices[0].message.content.strip()
        cleaned_output = ai_output.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_output)

    except Exception as e:
        return {"error": str(e)}