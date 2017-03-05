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


def connect():
    '''
    Establishes a connection to the Heroku ClearDB mySQL db

        Returns:
                [connection] database connection object
    '''
    # Connect to the database
    try:
        print "Attempting connection to database..."
        connection = pymysql.connect(host='us-cdbr-iron-east-04.cleardb.net',
                                     port=int(DB_PORT),
                                     user=DB_USER,
                                     password=DB_PASSWORD,
                                     db=DB_NAME,
                                     autocommit=True,
                                     cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        raise
    else:
        print "Database successfully connected."
        return connection

def get_engine():
    '''
    Creates and returns sqlalchemy engine for database storage
        Returns:
                [engine] the sqlalchemy engine
    '''
    engine = create_engine(DB_URL, echo=False)
    return engine

def send_to_db(df,engine,name):
    '''
    Sends the data in the pandas dataframe to a table

        Args:
            [df,engine,name] pandas dataframe/sqlalchemy engine/table name
    '''
    df.to_sql(con=engine, name=name, if_exists='append', index=False)

def get_access_tokens():
    '''
    Retrieves the Slack user access token from the database

    Args:
            [user_id] the id of the user to query in the db

    Returns:
            [tokens] (list) users oauth tokens
    '''
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT access_token FROM `users`"
            cursor.execute(sql)
            tokens = cursor.fetchall()
            print tokens
            return tokens
            # for user in users:
            #     print user
                # if user['user_id'] == user_id:
                #     if user_name != user['name'] and user_name != None:
                #         sql = "UPDATE user SET name=%s WHERE user_id=%s"
                #         data = (user_name,user_id)
                #         cursor.execute(sql,data)

    except Exception as e:
        raise
    else:
        print "Success retrieving user access tokens."
    finally:
        connection.close()

def get_bot_access_tokens():
    '''
    Retrieves the Slack bot access token from the database

    Args:
            [user_id] the id of the user to query in the db

    Returns:
            [tokens] (list) bot oauth tokens
    '''
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = '''SELECT DISTINCT bot_access_token FROM `users`'''
            cursor.execute(sql)
            tokens = cursor.fetchall()
            print tokens
            return tokens
    except Exception as e:
        raise
    else:
        print "Success retrieving bot access token."
    finally:
        connection.close()

def get_bot_user_id(token):
    '''
    Retrieves the Slack bot user id

    Args:
            [user_id] the id of the user to query in the db

    Returns:
            [bot_user_id] (string) bot user id
    '''
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT bot_user_id FROM `users` WHERE token=%s"
            data = (token)
            cursor.execute(sql,data)
            users = cursor.fetchall()
            for user in users:
                print user
                if user['user_id'] == user_id:
                    bot_user_id = user['bot_user_id']
                    return bot_user_id
    except Exception as e:
        raise
    else:
        print "Success retrieving bot user id."
    finally:
        connection.close()
