import sys
sys.path.append('C:/HKMU_FYP')
from Analyzer.Code_Analyzer.Class_Analyzer import analyze_class
from Analyzer.Code_Analyzer.Method_Analyzer import analyze_method
from Analyzer.Code_Analyzer.Variable_Analyzer import analyze_variable
from Model.Class_Model import insert_components
from Model.Method_Model import insert_method
from Model.Variable_Model import insert_variable
from Config.dbConfig import db_connect

def process_file(file_location):
    # Analyze the file
    analyzed_class = analyze_class(file_location)
    analyzed_method = analyze_method(file_location)
    analyzed_variable = analyze_variable(file_location)

    # Get database connection
    db, cursor = db_connect()
    if cursor is None:
        print("Failed to establish database connection")
        return

    try:
        # Insert components first
        insert_components(analyzed_class, db, cursor)
        
        # Insert methods second (since they depend on components)
        insert_method(analyzed_method, db, cursor)
        
        # Insert variables last (since they might depend on both components and methods)
        insert_variable(analyzed_variable, db, cursor)
        
        db.commit()
        print("All data inserted successfully")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        db.rollback()
    finally:
        if db and db.is_connected():
            cursor.close()
            db.close()
            print("Database connection closed.")

if __name__ == "__main__":
    file_location = "project_sample/library_management_python/Controllers/AdminManager.py"
    process_file(file_location)