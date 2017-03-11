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
    print "connect()"
    # Connect to the database
    try:
        print "  Attempting connection to database..."
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
        print "  Database successfully connected."
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
    print "send_to_db(df,engine,name)"

    if name=="messages":
        connection = connect()
        try:
            with connection.cursor() as cursor:
                # Read a single record
                event = df.iloc[0]['event']
                team_id = df.iloc[0]['team_id']
                channel = df.iloc[0]['channel']
                ts = df.iloc[0]['ts']
                print "  EVENT:",event
                print "  TEAM_ID:",team_id
                print "  TS:",ts

                sql = "SELECT * FROM `messages` WHERE event=%s AND team_id=%s AND channel=%s"
                data = (event,team_id,channel)
                cursor.execute(sql,data)
                messages = cursor.fetchall()
                print "  messages: ",messages
                if messages:
                    sql = "UPDATE `messages` SET ts=%s WHERE event=%s AND team_id=%s AND channel=%s"
                    data = (ts,event,team_id,channel)
                    cursor.execute(sql,data)
                else:
                    df.to_sql(con=engine, name=name, if_exists='append', index=False)
        except Exception as e:
            raise
        else:
            print "  Updated members table of database."
        finally:
            connection.close()
    else:
        df.to_sql(con=engine, name=name, if_exists='append', index=False)

def get_access_token(user_id):
    '''
    Retrieves the Slack user access token from the database

    Args:
            [user_id] the id of the user to query in the db

    Returns:
            [tokens] (string) users oauth token
    '''
    print "get_access_token(user_id)"

    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT access_token FROM `users` WHERE user_id=%s"
            data = (user_id)
            cursor.execute(sql,data)
            token = cursor.fetchall()
            print "  token: ",token
            print "  token[0]['access_token']: ",token[0]['access_token']
            return token[0]['access_token']
    except Exception as e:
        raise
    else:
        print "  Success retrieving user access tokens."
    finally:
        connection.close()

def get_bot_access_token(user_id):
    '''
    Retrieves the Slack bot access token from the database

    Returns:
            [token] (str) bot oauth access token
    '''
    print "get_bot_access_token(user_id)"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT bot_access_token FROM `users` WHERE user_id=%s"
            data = (user_id)
            cursor.execute(sql,data)
            token = cursor.fetchall()
            print "  token: ",token[0]['bot_access_token']
            return token[0]['bot_access_token']
    except Exception as e:
        raise
    else:
        print "  Success retrieving bot access token."
    finally:
        connection.close()

def get_bot_user_id(token):
    '''
    Retrieves the Slack bot user id

    Args:
            [token] (str) the bot access token

    Returns:
            [bot_user_id] (str) bot user id
    '''
    print "get_bot_user_id(token)"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT bot_user_id FROM `users` WHERE bot_access_token=%s"
            data = (token)
            cursor.execute(sql,data)
            response = cursor.fetchall()
            bot_user_id = response[0]['bot_user_id']
            print "  bot_user_id: ",bot_user_id
            return bot_user_id
    except Exception as e:
        raise
    else:
        print "  Success retrieving bot user id."
    finally:
        connection.close()

def get_team_id(user_id):
    '''
    Retrieves the Slack team_id of the given user_id

    Args:
            [user_id] (str) The id of the user.

    Returns:
            [team_id] (str) The id of the team the user is in.
    '''
    print "get_team_id(user_id)"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT DISTINCT team_id FROM `users` WHERE user_id=%s"
            data = (user_id)
            cursor.execute(sql,data)
            response = cursor.fetchall()
            team_id = response[0]['team_id']
            print "  team_id: ",team_id
            return team_id
    except Exception as e:
        raise
    else:
        print "  Success retrieving team_id."
    finally:
        connection.close()

def log_message_ts(ts,channel,event,team_id):
    '''
    Logs an incoming message timestamp in the database for the purpose of eventually cleaning up the main message channel

    Args:
            [ts] (str) The timestamp of the message
            [channel] (str) The channel the message was posted in
            [event] (str) The event type that the timestamp correlates to
            [team_id] (str) The id of the team in which the message was sent
    '''
    print "log_message_ts(ts,channel)"
    values = {"event": event, "channel": channel, "ts": ts, "team_id": team_id}
    df = pd.DataFrame(values, index=[0])
    engine = get_engine()
    send_to_db(df,engine,'messages')

def clear_ts_messages(team_id):
    '''
    Deletes the timestamped messages from the database

    Args:
            [team_id] (str) The id of the team in which the message was sent
    '''
    connection = connect()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM `messages` WHERE team_id=%s"
            data = (team_id)
            cursor.execute(sql,data)
    except Exception as e:
        raise
    else:
        print "  Successfully deleted entries from team's messages table."
    finally:
        connection.close()

def get_ts(channel,event,team_id):
    '''
    Retrieves the original message timestamp from the database

    Args:
            [channel] (str) The channel the message was posted in
            [event] (str) The event type that the timestamp correlates to
            [team_id] (str) The id of the team in which the message was sent
    '''
    print "get_ts(channel,event,team_id)"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT ts FROM `messages` WHERE team_id=%s AND channel=%s AND event=%s"
            data = (team_id,channel,event)
            cursor.execute(sql,data)
            ts_data = cursor.fetchall()
            ts = ts_data[0]['ts']
            return ts
    except Exception as e:
        raise
    else:
        print "  Successfully retrieved ts from db"
    finally:
        connection.close()

def get_bot_im_id(user_id,team_id):
    '''
    Retrieves bot_im_id from the users table of the db

    Args:
            [user_id] (str) The id of the user
            [team_id] (str) The id of the team
    '''
    print "get_bot_im_id(user_id,team_id)"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT bot_im_id FROM `users` WHERE user_id=%s AND team_id=%s"
            data = (user_id,team_id)
            cursor.execute(sql,data)
            user_data = cursor.fetchall()
            bot_im_id = user_data[0]['bot_im_id']
            return bot_im_id
    except Exception as e:
        raise
    else:
        print "  Successfully retrieved bot_im_id from db"
    finally:
        connection.close()
