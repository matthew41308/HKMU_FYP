import pymysql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

def insert_components(analyzed_class, db, cursor):
    """
    Insert component information into the database
    Links components with their organizations if they exist
    """
    if not analyzed_class.get("components"):
        return

    if cursor is None:
        print("Failed to establish database connection")
        return

    try:
        for component in analyzed_class["components"]:
            component_name = component.get("component_name")
            component_type = component.get("component_type")
            description = component.get("description")
            organization_name = component.get("organization_name")
            file_location=component.get("file_location")
            # Skip if required fields are missing
            if not all([component_name, component_type]):
                continue

            # Get organization_id if organization_name exists
            organization_id = None
            if organization_name:
                cursor.execute(
                    "SELECT organization_id FROM organizations WHERE organization_name = %s",
                    (organization_name,)
                )
                result = cursor.fetchone()
                if result:
                    organization_id = result['organization_id']
                    print(f"📂 Found organization_id {organization_id} for {organization_name}")
                else:
                    print(f"⚠️ Organization '{organization_name}' not found in database")

            # Insert component with organization_id if available
            if organization_id:
                sql = """
                    INSERT INTO components 
                    (component_name, component_type, description, organization_id,file_location) 
                    VALUES (%s, %s, %s, %s,%s)
                """
                values = (component_name, component_type, description, organization_id,file_location)
            else:
                sql = """
                    INSERT INTO components 
                    (component_name, component_type, description,file_location) 
                    VALUES (%s, %s, %s,%s)
                """
                values = (component_name, component_type, description,file_location)
            
            cursor.execute(sql, values)
            db.commit()
            print(f"✅ Component '{component_name}' inserted successfully")

    except pymysql.Error as err:
        print(f"❌ Database error in insert_components: {err}")
        db.rollback()
        raise
    except Exception as e:
        print(f"❌ Unexpected error in insert_components: {e}")
        db.rollback()
        raise