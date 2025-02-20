import mysql.connector
import os
from datetime import datetime
import json

def get_json_for_UseCase(db,cursor):
    if cursor is None:
        print("Failed to establish database connection")
        return None

    all_data = {
        'components': [],
        'methods': [],
        'method_parameters': [],
        'variables': []
    }

    try:
        # Fetch components
        cursor.execute("SELECT * FROM components")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            component_dict = dict(zip(columns, row))
            all_data['components'].append(component_dict)

        # Fetch methods
        cursor.execute("SELECT * FROM methods")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            method_dict = dict(zip(columns, row))
            all_data['methods'].append(method_dict)

        # Fetch method parameters
        cursor.execute("SELECT * FROM methodparameters")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            param_dict = dict(zip(columns, row))
            all_data['method_parameters'].append(param_dict)

        # Fetch variables
        cursor.execute("SELECT * FROM variables")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            variable_dict = dict(zip(columns, row))
            all_data['variables'].append(variable_dict)

        return all_data

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return None
    finally:
        if db and db.is_connected():
            cursor.close()
            db.close()
            print("Database connection closed.")



# Function to print the data in a more readable format
