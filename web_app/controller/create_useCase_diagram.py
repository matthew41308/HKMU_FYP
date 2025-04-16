import sys
import os
import gzip
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from flask import current_app
from web_app.model.json_for_useCase import get_json_for_useCase
import json
from datetime import datetime

def export_to_json(data, project_name,json_dir):
    error_msg=[]
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
        print(f"Created directory: {json_dir}")

    # Determine the attempt number based on existing files for the provided project_name.
    attempt = 1
    # Check for any files that match the pattern "{project_name}_<number>.<ext>"
    for filename in os.listdir(json_dir):
        # Use re.escape in case the project_name contains special regex characters.
        match = re.match(rf"^{re.escape(project_name)}_(\d+)\.", filename)
        if match:
            current_attempt = int(match.group(1))
            if current_attempt >= attempt:
                attempt = current_attempt + 1

    # Build filenames using the attempt count.
    json_filename = os.path.join(json_dir, f"{project_name}_{attempt}.json")
    text_filename = os.path.join(json_dir, f"{project_name}_{attempt}.txt")
    gzip_json_filename = os.path.join(json_dir, f"{project_name}_{attempt}.json.gz")

    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

    structured_data = {
        "metadata": {
            "project_name": project_name,
            "export_timestamp": datetime.now().isoformat()
        },
        "schemas": {},
        "data": {}
    }

    for table_name, records in data.items():
        if records:
            schema = list(records[0].keys())
            structured_data["schemas"][table_name] = schema
            structured_data["data"][table_name] = [
                [record[field] for field in schema]
                for record in records
            ]

    try:
        # Serialize JSON data as a compact string (without extra whitespace)
        serialized_data = json.dumps(structured_data, cls=CustomJSONEncoder, separators=(',', ':'))
        
        # Write the JSON file
        with open(json_filename, 'w', encoding='utf-8') as f:
            f.write(serialized_data)
        print(f"Data exported successfully to {json_filename}")

        # Write the minified JSON to a gzip-compressed file.
        with gzip.open(gzip_json_filename, 'wt', encoding='utf-8') as f:
            f.write(serialized_data)
        print(f"Data exported successfully to {gzip_json_filename}")

        # Create a text file version by stripping out all double quotes.
        text_data = serialized_data.replace('"', '')
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(text_data)
        print(f"Data exported in text form to {text_filename}")

        return json_filename,error_msg
    except Exception as e:
        error_msg.extend(f"Error exporting to JSON/text: {e}")
        return json_filename,error_msg

def print_data(data):
    if data is None:
        print("No data retrieved")
        return

    for table_name, records in data.items():
        print(f"\n=== {table_name.upper()} ===")
        if not records:
            print("No records found")
            continue
        
        print(f"Total records: {len(records)}")
        if records:
            print("Fields:", ", ".join(records[0].keys()))
            print("\nFirst record example:")
            for key, value in records[0].items():
                print(f"{key}: {value}")

if __name__=="__main__":
    db=current_app.config["db"]
    cursor = current_app.config["cursor"]
    result = get_json_for_useCase(db, cursor)
    # Print summary of the data
    print_data(result)
    project_name = "library_management"
    #export_to_json(result, project_name)