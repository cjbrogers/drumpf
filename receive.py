# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response
app = Flask(__name__)

from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests

import slackprovider
from slacker import Slacker

from sqlalchemy import create_engine
import pymysql
import pymysql.cursors

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')

# slack_client = slackprovider.get_slack_client()
slack = Slacker(os.environ.get('SLACK_USER_TOKEN'))

BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

'''
Establishes a connection to the mySQL db
@return [connection]
'''
def connect():
    # Connect to the database
    try:
        print "Attempting connection to database..."
        connection = pymysql.connect(host='localhost',
                                     port=3306,
                                     user='root',
                                     password='jamesonrogers',
                                     db='drumpf',
                                     cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        raise
    else:
        print "Database successfully connected."
        return connection

def get_user_token(user_id):
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
                    token = user['token']
                    return token
    except Exception as e:
        raise
    else:
        print "Data successfully stored."
    finally:
        connection.close()

# handles interactive button responses for donny_drumpfbot
@app.route('/actions', methods=['POST'])
def inbound():

    payload = request.form.get('payload')
    data = json.loads(payload)
    token = data['token']
    if token == SLACK_VERIFICATION_TOKEN:
        print 'TOKEN is good!'
        # print data
        response_url = data['response_url']
        channel_info = data['channel']
        channel_id = channel_info['id']
        user_info = data['user']
        user_id = user_info['id']
        user_name = user_info['name']
        actions = data['actions'][0]
        value = actions['value']
        print "Channel ID: ",channel_id
        print 'User sending message: ',user_name
        print "Value received: ",value

        token = get_user_token(user_id)
        slack = Slacker(token)
        slack.chat.post_message(channel=channel_id,text = AT_BOT +" {}".format(value),as_user=True)
    return Response(), 200

@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
