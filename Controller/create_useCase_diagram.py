import sys
sys.path.append('C:/HKMU_FYP')
from Config.dbConfig import db_connect
from Config.dbConfig import db_connect
from Model.Json_for_UseCase import get_json_for_UseCase
import json
import os
from datetime import datetime

def export_to_json(data, project_name):
    if data is None:
        print("No data to export")
        return

    json_dir = "Json_toAI"
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
        print(f"Created directory: {json_dir}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{json_dir}/{project_name}_{timestamp}.json"

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
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, cls=CustomJSONEncoder, separators=(',', ':'))  # Remove whitespace
        print(f"Data exported successfully to {filename}")
        return filename
    except Exception as e:
        print(f"Error exporting to JSON: {e}")
        return None

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
    db,cursor=db_connect()
    result=get_json_for_UseCase(db,cursor)
    # Print summary of the data
    print_data(result)
    project_name="library_management"
    json_file=export_to_json(result,project_name)