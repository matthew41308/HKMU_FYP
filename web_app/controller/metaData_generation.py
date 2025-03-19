import sys
import os
from collections import deque
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from analyzer.class_analyzer import analyze_class
from analyzer.method_analyzer import analyze_method
from analyzer.variable_analyzer import analyze_variable
from analyzer.organization_analyzer import analyze_organization
from model.class_model import insert_components
from model.method_model import insert_method
from model.variable_model import insert_variable
from model.organization_model import insert_organization
from config.dbConfig import db_connect,db,cursor,isDBconnected

def process_file(file_location):
    # Analyze the file
    global db,cursor,isDBconnected
    
    # Skip if not a Python file
    if not file_location.endswith('.py'):
        return
    
    # Skip __init__.py files
    if os.path.basename(file_location) == '__init__.py':
        return
    
    print(f"Processing file: {file_location}")
    analyzed_class = analyze_class(file_location)
    analyzed_method = analyze_method(file_location)
    analyzed_variable = analyze_variable(file_location)

    if not isDBconnected:
        db, cursor = db_connect()
        if cursor is None:
            print("Failed to establish database connection")
            return

    try:
        insert_components(analyzed_class, db, cursor)
        insert_method(analyzed_method, db, cursor)
        insert_variable(analyzed_variable, db, cursor)
        db.commit()
        print(f"✅ All data inserted successfully for {file_location}")
        
    except Exception as e:
        print(f"❌ Error during processing {file_location}: {e}")
        db.rollback()

def process_folder(root_folder):
    """
    Process folders and files using BFS traversal with separate
    queues for folders and files. At each BFS level:
      1. Gather all child folders and files from the current level.
      2. Process all folders in the level (using analyze_organization and
         insert_organization).
      3. Then process all files in the level (using process_file).
    Finally, prepare for the next level and repeat.
    
    Args:
        root_folder (str): Root directory path to start analysis.
    """
    global db, cursor, isDBconnected  # Assume these are defined elsewhere

    # Connect to database if not connected.
    if not isDBconnected:
        db, cursor = db_connect()
        if cursor is None:
            print("❌ Failed to establish database connection")
            return

    try:
        # Initialize two queues:
        # folder_queue will store folders to be processed at the current or next level.
        # file_queue will store files to be processed at the current level.
        folder_queue = deque()
        file_queue = deque()

        # Start by listing the children of the root folder.
        # (We assume that the "root" folder itself is not subject to organization analysis.)
        try:
            for entry in os.listdir(root_folder):
                if entry.startswith('.') or entry == '__pycache__':
                    continue
                full_path = os.path.join(root_folder, entry)
                if os.path.isdir(full_path):
                    folder_queue.append(full_path)
                elif os.path.isfile(full_path):
                    file_queue.append(full_path)
        except PermissionError:
            print(f"❌ Permission denied accessing {root_folder}")
            return

        level = 1  # Level 1: children of root_folder.
        # Continue BFS while there are any nodes (folders or files) at the current level.
        while folder_queue or file_queue:
            print(f"\n--- Processing BFS Level {level} ---")

            # Get all folder nodes (and clear the folder_queue for next level)
            current_level_folders = list(folder_queue)
            folder_queue.clear()

            # Get all file nodes of the current level (and clear the file_queue)
            current_level_files = list(file_queue)
            file_queue.clear()

            # Process all folder nodes:
            for folder in current_level_folders:
                try:
                    analyzed_organization = analyze_organization(folder)
                    insert_organization(analyzed_organization, db, cursor)
                    db.commit()
                except Exception as e:
                    print(f"❌ Error processing folder {folder}: {e}")
                    db.rollback()

            # Now process all file nodes in the current level:
            for file_path in current_level_files:
                try:
                    process_file(file_path)
                except Exception as e:
                    print(f"❌ Error processing file {file_path}: {e}")

            # After processing the current level, prepare the nodes for the next level.
            # For every folder that was processed in this level, look for its children.
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
                    print(f"❌ Permission denied accessing {folder}")
                    continue

            level += 1

    except Exception as e:
        print(f"❌ Error during folder processing: {e}")
        db.rollback()

    finally:
        if isDBconnected:
            cursor.close()
            db.close()
            isDBconnected = False
            print("\n✅ Database connection closed.")

if __name__ == "__main__":
    if not isDBconnected :
        db, cursor = db_connect()
        if cursor is None:
            print("❌ Failed to establish database connection")
    # Example usage
    project_root = "project_sample/library_management_python"
    result=process_folder(project_root)