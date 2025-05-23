import sys
import os
from collections import deque
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from web_app.analyzer.component_analyzer import analyze_component
from web_app.analyzer.method_analyzer import analyze_method
from web_app.analyzer.variable_analyzer import analyze_variable
from web_app.analyzer.organization_analyzer import analyze_organization
from web_app.model.component_model import insert_components
from web_app.model.method_model import insert_method
from web_app.model.variable_model import insert_variable
from web_app.model.organization_model import insert_organization
def process_file(file_location):
    error_msg=[]

    # Skip if not a Python file
    if not file_location.endswith('.py'):
        return []

    # Skip __init__.py files
    if os.path.basename(file_location) == '__init__.py':
        return []

    print(f"Processing file: {file_location}")
    analyzed_component = analyze_component(file_location)
    analyzed_method = analyze_method(file_location)
    analyzed_variable = analyze_variable(file_location)

    try:
        insert_components(analyzed_component)
    except Exception as e:
        error_msg.extend(f"Error during processing insert_components of {file_location} at process_file: {e}")

        return error_msg
    try:
        insert_method(analyzed_method)
    except Exception as e:
        error_msg.extend(f"Error during processing insert_method of{file_location} at process_file: {e}")

        return error_msg
    try:
        insert_variable(analyzed_variable)
    except Exception as e:
        error_msg.extend(f"Error during processing insert_variable of {file_location} at process_file: {e}")

        return error_msg
    
    print(f"✅ All data inserted successfully for {file_location}")
    return error_msg
    

def process_folder(root_folder):
    """
    Process folders and files using BFS traversal except analyze_organization() is DFS.
    
    Original behavior was to list the children of the root folder and begin analysis 
    on the next layer. In this updated version, we first analyze the root folder as
    the first layer. Then, we populate the BFS queues with its children.
    
    Args:
        root_folder (str): Root directory path to start analysis.
    """
    error_msg=[]

    try:
        # === Process the ROOT folder (first layer) ===
        print(f"Processing ROOT folder: {root_folder}")
        try:
            analyzed_organization = analyze_organization(root_folder)
            insert_organization(analyzed_organization)
        except Exception as e:
            error_msg.extend(f"Error processing insert_organization of folder at {root_folder} at process_folder: {e}")

        
        # Optionally, process Python files directly under the root folder.
        try:
            for entry in os.listdir(root_folder):
                if entry.startswith('.') or entry == '__pycache__':
                    continue
                full_path = os.path.join(root_folder, entry)
                if os.path.isfile(full_path):
                    error_msg.extend(process_file(full_path))
        except PermissionError:
            error_msg.extend(f"Permission denied accessing files in {root_folder} at process_folder")

        # === Initialize the BFS queues with the children directories of the root folder ===
        folder_queue = deque()
        file_queue = deque()
        try:
            for entry in os.listdir(root_folder):
                if entry.startswith('.') or entry == '__pycache__':
                    continue
                full_path = os.path.join(root_folder, entry)
                if os.path.isdir(full_path):
                    folder_queue.append(full_path)
                # We already processed files in the root folder above.
        except PermissionError:
            error_msg.extend(f"Permission denied accessing {root_folder} at process_folder")

        level = 2  # Since we already handled the first layer (root folder)
        while folder_queue or file_queue:
            print(f"\n--- Processing BFS Level {level} ---")

            # Process all folder nodes in the current level.
            current_level_folders = list(folder_queue)
            folder_queue.clear()

            # Process all file nodes in the current level.
            current_level_files = list(file_queue)
            file_queue.clear()

            # Process all Python files in the current level.
            for file_path in current_level_files:
                error_msg.extend(process_file(file_path))
            # For every folder in the current level, add its children for analysis.
            for folder in current_level_folders:
                try:
                    for entry in os.listdir(folder):
                        if entry.startswith('.') or entry == '__pycache__':
                            continue
                        full_path = os.path.join(folder, entry)
                        if os.path.isdir(full_path):
                            folder_queue.append(full_path)
                        elif os.path.isfile(full_path):
                            file_queue.append(full_path)
                except PermissionError:
                    error_msg.extend(f"Permission denied accessing {folder}")
                    continue

            level += 1

    except Exception as e:
        error_msg.extend(f"Error during folder processing: {e}")

    return error_msg

if __name__ == "__main__":
    # Example usage
    project_root = "project_sample/library_management_python"
    process_folder(project_root)