import os
from flask import Flask, request
from slackclient import SlackClient
from sqlalchemy import create_engine
import pymysql
import pymysql.cursors
import pandas as pd

import urllib
import unicodedata
client_id = os.environ["SLACK_OAUTH_CLIENT_ID"]
client_secret = os.environ["SLACK_OAUTH_CLIENT_SECRET"]
oauth_scope = os.environ["SLACK_BOT_SCOPE"]

app = Flask(__name__)

# '''
# Establishes a connection to the mySQL db
# @return [connection]
# '''
# def connect():
#     # Connect to the database
#     try:
#         print "Attempting connection to database..."
#         connection = pymysql.connect(host='localhost',
#                                      port=3306,
#                                      user='root',
#                                      password='jamesonrogers',
#                                      db='drumpf',
#                                      cursorclass=pymysql.cursors.DictCursor)
#     except Exception as e:
#         raise
#     else:
#         print "Database successfully connected."
#         return connection
#
# def send_to_db(token,uid,name):
#     unicodedata.normalize('NFKD', token).encode('ascii','ignore')
#     unicodedata.normalize('NFKD', uid).encode('ascii','ignore')
#     unicodedata.normalize('NFKD', name).encode('ascii','ignore')
#     connection = connect()
#     try:
#         with connection.cursor() as cursor:
#             # Read a single record
#             sql = '''INSERT INTO `drumpf`.`user` VALUES ('{}','{}','{}')'''.format(token,uid,name)
#             print sql
#             # args = (token,uid,name)
#             cursor.execute(sql)
#     except Exception as e:
#         raise
#     else:
#         print "Data successfully stored."
#     finally:
#         connection.close()

# the beggining of the Add to Slack button OAuth process
@app.route("/auth", methods=["GET"])
def pre_install():
    redirect_uri = "https://drumpfbot.herokuapp.com/auth/finish"
    return '''
      <a href="https://slack.com/oauth/authorize?scope={0}&client_id={1}&redirect_uri={2}">
          <img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
      </a>
    '''.format(oauth_scope, client_id, redirect_uri)

@app.route("/auth/finish", methods=["GET", "POST"])
def post_install():
    # redirect_uri = "https%3A%2F%2F43ff30f2.ngrok.io%2Ffinish_auth"
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
    print(auth_response['access_token'])
    os.environ["SLACK_USER_TOKEN"] = auth_response['access_token']
    print(auth_response['bot']['bot_access_token'])
    os.environ["SLACK_BOT_TOKEN"] = auth_response['bot']['bot_access_token']

    # Don't forget to let the user know that auth has succeeded!
    return "Auth complete!"


# # the beginning of the Sign In to Slack OAuth process.
# # we can get the user tokens from the return of this call
# @app.route("/signin", methods=["GET"])
# def pre_signin():
#     return '''
#       <a href="https://slack.com/oauth/authorize?scope=identity.basic,identity.email,identity.team,identity.avatar&client_id=122416745729.127817802451">
#
#           <img alt="Sign in with Slack" height="40" width="172" src="https://platform.slack-edge.com/img/sign_in_with_slack.png" srcset="https://platform.slack-edge.com/img/sign_in_with_slack.png 1x, https://platform.slack-edge.com/img/sign_in_with_slack@2x.png 2x" />
#
#       </a>
#     '''
# @app.route("/signin/finish", methods=["GET", "POST"])
# def post_signin():
#     # Retrieve the auth code from the request params
#     auth_code = request.args['code']
#
#     # An empty string is a valid token for this request
#     sc = SlackClient("")
#
#     # Request the auth tokens from Slack
#     auth_response = sc.api_call(
#         "oauth.access",
#         client_id=client_id,
#         client_secret=client_secret,
#         code=auth_code
#     )
#
#     # Save the bot token to an environmental variable or to your data store
#     # for later use
#     print(auth_response)
#     token = auth_response['access_token']
#     uid = auth_response['user']['id']
#     name = auth_response['user']['name']
#
#     values = {"token": token, "uid": uid, "name": name}
#     df = pd.DataFrame(values, index=[0])
#     engine = create_engine('mysql+pymysql://root:jamesonrogers@localhost:3306/drumpf', echo=False)
#     df.to_sql(con=engine, name='user', if_exists='append', index=False)
#
#     # TODO: add the above auth_response elements to a DB
#     # send_to_db(token,uid,name)
#
#     # Don't forget to let the user know that auth has succeeded!
#     return "<h1>Welcome to Drumpf!</h1> You can now close this window and focus on making card games great again."

if __name__ == "__main__":
    app.run(debug=True)
