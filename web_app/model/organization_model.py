import pymysql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from analyzer.organization_analyzer import analyze_organization
from flask import current_app

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def insert_organization(analyzed_organization):
    """
    Insert organizations into the database
    Args:
        analyzed_organization: Dictionary containing organization information
        db: Database connection
        cursor: Database cursor
    """
    if not analyzed_organization.get("organizations"):
        return

    db = current_app.config["db"]
    cursor = current_app.config["cursor"]
            
    try:
        for organization in analyzed_organization["organizations"]:
            # Extract organization details with default values
            organization_details = {
                'organization_name': organization.get('organization_name'),
                'organization_path': organization.get('organization_path'),
                'organization_type': organization.get('organization_type'),
            }

            # Validate required fields
            if not organization_details['organization_name']:
                print("❌ Skipping organization: Missing organization name")
                continue

            # Prepare organization insertion
            sql = """
                INSERT INTO organizations 
                (organization_name, organization_path,organization_type) 
                VALUES (%s, %s, %s)
            """
            values = (
                organization_details['organization_name'],
                organization_details['organization_path'],
                organization_details['organization_type']
            )

            # Insert organization
            cursor.execute(sql, values)
            db.commit()
            print(f"✅ Organization '{organization_details['organization_name']}' inserted successfully")

    except pymysql.Error as err:
        print(f"❌ Database error: {err}")
        db.rollback()
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        db.rollback()
        raise

if __name__=="__main__":
    # Example usage
    project_root = "project_sample/library_management_python"
    result=analyze_organization(project_root)
    print(result)
    insert_organization(result)
