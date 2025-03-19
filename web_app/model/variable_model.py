import pymysql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def insert_variable(analyzed_variable, db, cursor):
    """
    Insert variables into the database
    Args:
        analyzed_variable: Dictionary containing variable information
        db: Database connection
        cursor: Database cursor
    """
    if cursor is None:
        print("❌ Failed to establish database connection")
        return

    if not analyzed_variable.get("variables"):
        print("⚠️ No variables to insert")
        return
        
    try:
        for variable in analyzed_variable["variables"]:
            # Extract variable details with default values
            var_details = {
                'name': variable.get('variable_name'),
                'type': variable.get('variable_type'),
                'scope': variable.get('scope').value if variable.get('scope') else None,
                'is_constant': variable.get('is_constant', False),
                'is_static': variable.get('is_static', False),
                'visibility': variable.get('visibility'),
                'description': variable.get('description'),
                'component_name': variable.get('component_name'),
                'method_name': variable.get('method_name'),
                'line_number': variable.get('line_number'),
                'declaration_type': variable.get('declaration_type')
            }

            # Validate required fields
            if not var_details['name']:
                print("❌ Skipping variable: Missing variable name")
                continue

            # Get component_id if component_name exists
            component_id = None
            if var_details['component_name']:
                cursor.execute(
                    "SELECT component_id FROM components WHERE component_name = %s",
                    (var_details['component_name'],)
                )
                result = cursor.fetchone()
                component_id = result['component_id'] if result else None

            # Get method_id if method_name exists
            method_id = None
            if var_details['method_name']:
                cursor.execute(
                    "SELECT method_id FROM methods WHERE method_name = %s",
                    (var_details['method_name'],)
                )
                result = cursor.fetchone()
                method_id = result['method_id'] if result else None

            # Insert variable
            sql = """
                INSERT INTO variables
                (component_id, method_id, variable_name, variable_type, 
                 scope, is_constant, is_static, visibility, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                component_id,
                method_id,
                var_details['name'],
                var_details['type'],
                var_details['scope'],
                var_details['is_constant'],
                var_details['is_static'],
                var_details['visibility'],
                var_details['description']
            )
            
            try:
                cursor.execute(sql, values)
                db.commit()
                print(f"✅ Variable '{var_details['name']}' inserted successfully")
            except pymysql.Error as err:
                print(f"❌ Error inserting variable '{var_details['name']}': {err}")
                db.rollback()

    except pymysql.Error as err:
        print(f"❌ Database error: {err}")
        db.rollback()
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        db.rollback()
        raise
