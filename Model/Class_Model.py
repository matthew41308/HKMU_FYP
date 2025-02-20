import mysql.connector

def insert_components(analyzed_class,db,cursor):
    if analyzed_class["components"] != None:
        if cursor is None:
            print("Failed to establish database connection")
            return
        try:
            for component in analyzed_class["components"]:
                component_name = component["component_name"]
                component_type = component["component_type"]
                description = component["description"]
                methods=component["methods"]

                sql = f"insert into components (component_name, component_type, description) values (%s,%s,%s)"
                values = (component_name,component_type,description)
                cursor.execute(sql, values)
                db.commit()
                print(cursor.rowcount, "record inserted into components.")

        except mysql.connector.Error as err:
            print(f"Database error in insert_method: {err}")
            raise
    