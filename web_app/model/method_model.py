import pymysql
import sys
import os
from flask import current_app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def insert_method(analyzed_method):
    """
    Insert method and its parameters into the database
    Args:
        analyzed_method: Dictionary containing method information
        db: Database connection
        cursor: Database cursor
    """
    if not analyzed_method.get("methods"):
        return

    db = current_app.config["db"]
    cursor = current_app.config["cursor"]
            
    try:
        for method in analyzed_method["methods"]:
            # Extract method details with default values
            method_details = {
                'location': method.get('location'),
                'method_name': method.get('method_name'),
                'return_type': method.get('return_type'),
                'visibility': method.get('visibility'),
                'is_static': method.get('is_static', False),
                'description': method.get('description'),
                'parameters': method.get('parameters', [])
            }

            # Validate required fields
            if not method_details['method_name']:
                print("❌ Skipping method: Missing method name")
                continue

            # Get component_id if location exists
            component_id = None
            if method_details['location']:
                cursor.execute(
                    "SELECT component_id FROM components WHERE component_name = %s",
                    (method_details['location'],)
                )
                result = cursor.fetchone()
                component_id = result['component_id'] if result else None

            # Prepare method insertion
            if component_id:
                sql = """
                    INSERT INTO methods 
                    (component_id, return_type, visibility, is_static, description, method_name) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    component_id,
                    method_details['return_type'],
                    method_details['visibility'],
                    method_details['is_static'],
                    method_details['description'],
                    method_details['method_name']
                )
            else:
                sql = """
                    INSERT INTO methods 
                    (return_type, visibility, is_static, description, method_name) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    method_details['return_type'],
                    method_details['visibility'],
                    method_details['is_static'],
                    method_details['description'],
                    method_details['method_name']
                )

            # Insert method
            cursor.execute(sql, values)
            db.commit()
            print(f"✅ Method '{method_details['method_name']}' inserted successfully")

            # Get the last inserted method_id
            method_id = cursor.lastrowid

            # Insert parameters
            for param in method_details['parameters']:
                param_details = {
                    'name': param.get('parameter_name'),
                    'type': param.get('parameter_type'),
                    'required': param.get('is_required', True),
                    'default': param.get('default_value'),
                    'description': param.get('description')
                }

                # Skip if parameter name is missing
                if not param_details['name']:
                    continue

                sql = """
                    INSERT INTO methodparameters 
                    (method_id, parameter_name, parameter_type, is_required, default_value, description) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    method_id,
                    param_details['name'],
                    param_details['type'],
                    param_details['required'],
                    param_details['default'],
                    param_details['description']
                )

                cursor.execute(sql, values)
                db.commit()
                print(f"✅ Parameter '{param_details['name']}' inserted for method '{method_details['method_name']}'")

    except pymysql.Error as err:
        print(f"❌ Database error: {err}")
        db.rollback()
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        db.rollback()
        raise
