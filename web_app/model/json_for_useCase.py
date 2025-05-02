import pymysql
import sys
import os
from flask import current_app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def prepare_json():
    error_msg=[]
    """
    Fetch all data from components, methods, method parameters, and variables tables
    Returns a dictionary containing all the data
    """
    db = current_app.config["db"]
    cursor = current_app.config["cursor"]


    all_data = {
        'organizations':[],
        'components': [],
        'methods': [],
        'method_parameters': [],
        'variables': []
    }

    tables = {
        'organizations':'organizations',
        'components': 'components',
        'methods': 'methods',
        'method_parameters': 'methodparameters',
        'variables': 'variables'
    }

    try:
        for key, table in tables.items():
            try:
                cursor.execute(f"SELECT * FROM {table}")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                # If using regular cursor
                if isinstance(rows[0], tuple):
                    all_data[key] = [dict(zip(columns, row)) for row in rows]
                # If using DictCursor
                else:
                    all_data[key] = rows

                print(f"✅ Successfully fetched {len(rows)} records from {table}")
                
            except pymysql.Error as e:
                error_msg.extend(f"Error fetching from {table}: {e}")
                all_data[key] = []

        return all_data,error_msg

    except Exception as e:
        error_msg.extend(f"Unexpected error: {e}")
        return all_data,error_msg

def print_formatted_data(data):
    """Helper function to print the data in a readable format"""
    if not data:
        print("No data to display")
        return

    for category, items in data.items():
        print(f"\n{'='*20} {category.upper()} {'='*20}")
        for item in items:
            print("\nRecord:")
            for key, value in item.items():
                print(f"  {key}: {value}")

if __name__ =="__main__":
    data = prepare_json()
    print_formatted_data(data)