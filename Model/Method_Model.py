import mysql.connector
from Config.dbConfig import db_connect,db,cursor
from mysql.connector import errorcode

def insert_method(analyzed_method):
    if __name__ == "Class_Model":
        if analyzed_method["methods"]!=None:
            for method in analyzed_method["methods"]:
                location = method["location"]
                method_name= method["method_name"]
                return_type=method["return_type"]
                visibility= method["visibility"]
                is_static=method["is_static"]
                description=method["description"]
                parameters = method["parameters"]
                db_connect
                sql = "select component_id from components where component_name = %s"
                cursor.execute(sql,location)
                component_id = cursor.fetchall()
                db.close()
                if component_id != None:
                    db_connect
                    sql="update methods set component_id = %s, return_type = %s, visbility = %s, description =%s where method_name = %s"
                    cursor.execute(sql,component_id,return_type,visibility,is_static,description, method_name)
    if __name__ == "__main__":
        
