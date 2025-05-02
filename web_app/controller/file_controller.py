import sys
import os
from pathlib import Path
from typing import Dict, Optional,Union
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from flask import current_app,jsonify
from model.json_for_useCase import prepare_json
import json
from datetime import datetime
import shutil
from werkzeug.utils import secure_filename
def safe_rm_tree(path: Path) -> bool:
    """
    Recursively delete *path* if it exists and is inside its expected parent.
    Returns True when something was removed, False when the directory was missing.
    """
    if not path.exists():
        return False

    # safety-belt: never allow traversal outside the user area
    expected_parent = path.parents[1]          # …/<user>/{Json_toAI|uploads}
    if not path.resolve().is_relative_to(expected_parent.resolve()):
        raise RuntimeError(f"Refusing to delete path outside user area: {path}")

    shutil.rmtree(path)
    return True

def export_to_json(data, project_name,user_name):
    error_msg=[]
    project_export_dir=f"{current_app.config['USERS_PATH']}/{user_name}/Json_toAI/{project_name}"
    if not os.path.exists(project_export_dir):
        os.makedirs(project_export_dir)
        print(f"Created directory: {project_export_dir}")

    # Build filenames using the attempt count.
    json_filename = os.path.join(project_export_dir, f"{project_name}.json")
    text_filename = os.path.join(project_export_dir, f"{project_name}.txt")

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

        # Create a text file version by stripping out all double quotes.
        text_data = serialized_data.replace('"', '')
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(text_data)
        print(f"Data exported in text form to {text_filename}")

        return json_filename,error_msg
    except Exception as e:
        error_msg.extend(f"Error exporting to JSON/text: {e}")
        return json_filename,error_msg
    
def is_ProjectExist(project_name):
    if os.path.exists(f"{current_app.config['USERS_PATH']}/{current_app.config['user_name']}/uploads/{project_name}"):
        return True
    
def _newest_txt_file(folder: Path) -> Optional[str]:
    """
    Return the newest *.txt file **inside `folder`** or ``None`` if there are none.
    """
    txt_files = [p for p in folder.glob("*.txt") if p.is_file()]
    if not txt_files:
        return None
    newest = max(txt_files, key=lambda p: p.stat().st_mtime)
    return newest.name


def get_user_repository() -> Dict[str, Optional[str]]:
    """
    Build a mapping

        {
          "<project_name from uploads>" : "<txt-file name in Json_toAI>/<project_name>",
          ...
        }

    • If the project *exists* in Json_toAI and contains at least one *.txt file,
      we return the newest file’s name.
    • Otherwise the value is ``None``.
    """
    users_path: str = current_app.config["USERS_PATH"]
    user_name: str = current_app.config["user_name"]

    uploads_root   = Path(users_path) / user_name / "uploads"
    exports_root   = Path(users_path) / user_name / "Json_toAI"

    if not uploads_root.exists():
        return {}

    result: Dict[str, Optional[str]] = {}

    # 1️⃣ iterate over first-level folders in /uploads
    for project_folder in uploads_root.iterdir():
        if not project_folder.is_dir():
            continue                      # skip stray files

        project_name = project_folder.name
        candidate_export_dir = exports_root / project_name

        # 2️⃣ look for a matching folder in Json_toAI
        if candidate_export_dir.is_dir():
            newest_txt = _newest_txt_file(candidate_export_dir)
            result[project_name] = newest_txt
        else:
            result[project_name] = None

    return result

def clear_user_repository(project_name: str) -> Dict[str, Union[bool, str]]:
    """
    Delete the *project_name* directory from both
        •  …/<user>/uploads/<project_name>
        •  …/<user>/Json_toAI/<project_name>

    Returns a dict with per-location status:

        {
          "uploads"  : True|False|"<error msg>",
          "Json_toAI": True|False|"<error msg>"
        }
    """
    if not project_name:
        return jsonify({"error": f"❌ Please enter project name"}), 500

    # sanitise so that “../../etc” can’t be injected
    safe_name = secure_filename(project_name)

    users_path = Path(current_app.config["USERS_PATH"])
    user_name  = current_app.config["user_name"]

    uploads_dir = users_path / user_name / "uploads"   / safe_name
    json_dir    = users_path / user_name / "Json_toAI" / safe_name

    result: Dict[str, Union[bool, str]] = {}

    for label, path in (("uploads", uploads_dir), ("Json_toAI", json_dir)):
        try:
            result[label] = safe_rm_tree(path)
        except Exception as exc:
            # capture the error string so the caller can inspect it
            result[label] = f"error: {exc}"
    
    db=current_app.config["db"]
    db.reset_db()

    return result
#This is for self testing
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
    cursor = current_app.config['cursor']
    result = prepare_json(db, cursor)
    # Print summary of the data
    print_data(result)
    project_name = "library_management"
    #export_to_json(result, project_name)