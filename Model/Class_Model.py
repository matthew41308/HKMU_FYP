import mysql.connector

from Config.dbConfig import db_connect,db,cursor
from mysql.connector import errorcode



def insert_components(analyzed_class):

    if analyzed_class["components"] != None:
        for component in analyzed_class["components"]:
            component_name = component["component_name"]
            component_type = component["component_type"]
            description = component["description"]
            db_connect
            sql = f"insert into components (component_name, component_type, description) values (%s,%s,%s)"
            values = (component_name,component_type,description)
            cursor.execute(sql, values)
            db.commit()
            print(cursor.rowcount, "record inserted into components.")

def insert_method():
    