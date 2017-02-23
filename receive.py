# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response, render_template
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests
import slackprovider
from slacker import Slacker
from sqlalchemy import create_engine
import pymysql
import pymysql.cursors
import pandas as pd

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')
client_id = os.environ["SLACK_OAUTH_CLIENT_ID"]
client_secret = os.environ["SLACK_OAUTH_CLIENT_SECRET"]
oauth_scope = os.environ["SLACK_BOT_SCOPE"]

# slack_client = slackprovider.get_slack_client()
# slack = Slacker(os.environ.get('SLACK_USER_TOKEN'))

BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_USER = os.environ.get("DB_USER")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_URL = os.environ.get("DB_URL")
app = Flask(__name__)

'''
Establishes a connection to the mySQL db
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
                        sql = '''UPDATE `user` SET name={}'''.format(user_name)
                        cursor.execute(sql)
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

        token = get_user_token(user_id,user_name)
        slack = Slacker(token)
        slack.chat.post_message(channel=channel_id,text = AT_BOT +" {}".format(value),as_user=True)
    return Response(), 200

# the beginning of the Sign In to Slack OAuth process.
# we can get the user tokens from the return of this call
@app.route("/signin", methods=["GET"])
def pre_signin():
    return '''
      <a href="https://slack.com/oauth/authorize?scope=chat:write:user&client_id=122416745729.127817802451">

          <img alt="Sign in with Slack" height="40" width="172" src="https://platform.slack-edge.com/img/sign_in_with_slack.png" srcset="https://platform.slack-edge.com/img/sign_in_with_slack.png 1x, https://platform.slack-edge.com/img/sign_in_with_slack@2x.png 2x" />

      </a>
    '''

@app.route("/signin/finish", methods=["GET", "POST"])
def post_signin():
    # Retrieve the auth code from the request params
    auth_code = request.args['code']

    # An empty string is a valid token for this request
    sc = SlackClient("")

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        "oauth.access",
        client_id=client_id,
        client_secret=client_secret,
        code=auth_code
    )

    # Save the bot token to an environmental variable or to your data store
    # for later use
    print(auth_response)
    token = auth_response['access_token']
    uid = auth_response['user_id']
    name = ""

    values = {"token": token, "uid": uid, "name": name}
    df = pd.DataFrame(values, index=[0])
    # engine = create_engine('mysql+pymysql://root:jamesonrogers@localhost:3306/drumpf', echo=False)
    engine = create_engine(DB_URL, echo=False)
    df.to_sql(con=engine, name='user', if_exists='append', index=False)

    # TODO: add the above auth_response elements to a DB
    # send_to_db(token,uid,name)

    # Don't forget to let the user know that auth has succeeded!
    return "<h1>Welcome to Drumpf!</h1> You can now <a href='https://drumpfbot.herokuapp.com/'>head back to the main page</a>, or just close this window."

@app.route('/', methods=['GET'])
def test():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
