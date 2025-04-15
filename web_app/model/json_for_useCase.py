import pymysql
import sys
import os
from config.dbConfig import db_connect, db, cursor, isDBconnected
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def get_json_for_useCase():
    """
    Fetch all data from components, methods, method parameters, and variables tables
    Returns a dictionary containing all the data
    """
    global cursor
    if cursor is None:
        db,cursor = db_connect()
        print("❌ Failed to establish database connection")
        return None

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
                print(f"❌ Error fetching from {table}: {e}")
                all_data[key] = []

        return all_data

    except pymysql.Error as err:
        print(f"❌ Database error: {err}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
    finally:
        pass

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

