import mysql.connector

def insert_method(analyzed_method,db,cursor):
    if analyzed_method["methods"] is not None:

        if cursor is None:
            print("Failed to establish database connection")
            return
            
        try:
            for method in analyzed_method["methods"]:
                location = method["location"]
                method_name = method["method_name"]
                return_type = method["return_type"]
                visibility = method["visibility"]
                is_static = method["is_static"]
                description = method["description"]
                parameters = method["parameters"]
                
                # Get component_id
                sql = "SELECT component_id FROM components WHERE component_name = %s"
                cursor.execute(sql, (location,))  # Note the comma to make it a tuple
                component_id = cursor.fetchone()  # Use fetchone() instead of fetchall()

                if component_id:
                    # Insert method with component_id
                    sql = """INSERT INTO methods 
                            (component_id, return_type, visibility, is_static, description, method_name) 
                            VALUES (%s, %s, %s, %s, %s, %s)"""
                    values = (component_id[0], return_type, visibility, is_static, description, method_name)
                    cursor.execute(sql, values)
                else:
                    # Insert method without component_id
                    sql = """INSERT INTO methods 
                            (return_type, visibility, is_static, description, method_name) 
                            VALUES (%s, %s, %s, %s, %s)"""
                    values = (return_type, visibility, is_static, description, method_name)
                    cursor.execute(sql, values)
                
                db.commit()
                
                # Get the last inserted method_id
                cursor.execute("SELECT LAST_INSERT_ID()")
                method_id = cursor.fetchone()[0]
                
                # Insert parameters
                for parameter in parameters:
                    parameter_name = parameter["parameter_name"]
                    parameter_type = parameter["parameter_type"]
                    is_required = parameter["is_required"]
                    default_value = parameter["default_value"]
                    param_description = parameter["description"]
                    
                    sql = """INSERT INTO methodparameters 
                            (method_id, parameter_name, parameter_type, is_required, default_value, description) 
                            VALUES (%s, %s, %s, %s, %s, %s)"""
                    values = (method_id, parameter_name, parameter_type, is_required, default_value, param_description)
                    cursor.execute(sql, values)
                    db.commit()
                    
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            raise
       