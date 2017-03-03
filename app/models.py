import os
from sqlalchemy import create_engine
import pymysql
import pymysql.cursors
import pandas as pd

DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_USER = os.environ.get("DB_USER")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_URL = os.environ.get("DB_URL")

'''
Establishes a connection to the Heroku ClearDB mySQL db
@return [connection]
'''
def connect():
    # Connect to the database
    try:
        print "Attempting connection to database..."
        connection = pymysql.connect(host='us-cdbr-iron-east-04.cleardb.net',
                                     port=int(DB_PORT),
                                     user=DB_USER,
                                     password=DB_PASSWORD,
                                     db=DB_NAME,
                                     cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        raise
    else:
        print "Database successfully connected."
        return connection

'''
Creates and returns sqlalchemy engine for database storage
@return [engine]
'''
def get_engine():
    engine = create_engine(DB_URL, echo=False)
    return engine

'''
Sends the data in the pandas dataframe to a table
@params [df,engine,name] pandas dataframe/sqlalchemy engine/table name
'''
def send_to_db(df,engine,name):
    df.to_sql(con=engine, name=name, if_exists='append', index=False)

'''
Retrieves the Slack user token from the database
@return [token] users oauth token
'''
def get_user_token(user_id,user_name):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = '''SELECT * FROM `user`'''
            cursor.execute(sql)
            users = cursor.fetchall()
            print users
            for user in users:
                print user
                if user['uid'] == user_id:
                    if user_name != user['name']:
                        sql = " UPDATE user SET name={} WHERE uid='{}' ".format(user_name,user['uid'])
                        cursor.execute(sql)
                    token = user['token']
                    return token
    except Exception as e:
        raise
    else:
        print "Data successfully stored."
    finally:
        connection.close()
