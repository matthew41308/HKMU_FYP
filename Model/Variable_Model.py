import mysql.connector


def insert_variable(analyzed_variable,db,cursor):
    if cursor is None:
        print("Failed to establish database connection")
        return
        
    try:
        variables = analyzed_variable["variables"]
        for variable in variables:
            variable_name = variable["variable_name"]
            variable_type = variable["variable_type"] 
            scope = variable["scope"].value
            is_constant = variable["is_constant"]
            is_static = variable["is_static"]
            visibility = variable["visibility"]
            description = variable["description"]
            component_name = variable["component_name"]
            method_name = variable["method_name"]
            line_number = variable["line_number"]
            declaration_type = variable["declaration_type"]

            # Get component_id
            sql = "SELECT component_id FROM components WHERE component_name = %s"
            cursor.execute(sql, (component_name,))
            component_id = cursor.fetchone()

            # Get method_id
            sql = "SELECT method_id FROM methods WHERE method_name = %s"
            cursor.execute(sql, (method_name,))
            method_id = cursor.fetchone()

            # Insert variable
            sql = """INSERT INTO variables
                     (component_id, method_id, variable_name, variable_type, 
                      scope, is_constant, is_static, visibility, description)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            values = (
                component_id[0] if component_id else None,
                method_id[0] if method_id else None,
                variable_name,
                variable_type,
                scope,
                is_constant,
                is_static,
                visibility,
                description
            )
            
            cursor.execute(sql, values)
            db.commit()

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        raise