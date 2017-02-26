# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response, render_template
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests
from slacker import Slacker
import pandas as pd
import model

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')
CLIENT_ID = os.environ["SLACK_OAUTH_CLIENT_ID"]
CLIENT_SECRET = os.environ["SLACK_OAUTH_CLIENT_SECRET"]
OAUTH_SCOPE = os.environ["SLACK_BOT_SCOPE"]

BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

app = Flask(__name__)

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

        token = model.get_user_token(user_id,user_name)
        slack = Slacker(token)
        resp = slack.chat.post_message(channel=channel_id,text = AT_BOT +" {}".format(value),as_user=True)
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

# end of the Slack signin process, appending relevant user information including tokens into the db
@app.route("/signin/finish", methods=["GET", "POST"])
def post_signin():
    # Retrieve the auth code from the request params
    auth_code = request.args['code']

    # An empty string is a valid token for this request
    sc = SlackClient("")

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        "oauth.access",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
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
    engine = model.get_engine()
    model.send_to_db(df,engine,'user')

    # Don't forget to let the user know that auth has succeeded!
    return "<h1>Welcome to Drumpf!</h1> You can now <a href='https://drumpfbot.herokuapp.com/'>head back to the main page</a>, or just close this window."

# the beggining of the Add to Slack button OAuth process
@app.route("/auth", methods=["GET"])
def pre_install():
    redirect_uri = "https://drumpfbot.herokuapp.com/auth/finish"
    return '''
      <a href="https://slack.com/oauth/authorize?scope={0}&client_id={1}&redirect_uri={2}">
          <img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
      </a>
    '''.format(OAUTH_SCOPE, CLIENT_ID, redirect_uri)

# completes the ouath add to slack process, adding relevant tokens to the database
@app.route("/auth/finish", methods=["GET", "POST"])
def post_install():
    redirect_uri = "https://drumpfbot.herokuapp.com/auth/finish"
    # Retrieve the auth code from the request params
    auth_code = request.args['code']

    # An empty string is a valid token for this request
    sc = SlackClient("")

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        "oauth.access",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=redirect_uri,
        code=auth_code
    )

    # Save the bot token to an environmental variable or to your data store
    # for later use
    print(auth_response)
    print(auth_response['access_token'])
    access_token = auth_response['access_token']
    print(auth_response['bot']['bot_access_token'])
    bot_access_token = auth_response['bot']['bot_access_token']
    team_id = auth_response['team_id']
    values = {"access_token": access_token, "bot_access_token": bot_access_token, "team_id": team_id}

    df = pd.DataFrame(values, index=[0])
    engine = model.get_engine()
    model.send_to_db(df,engine,'team')

    # Don't forget to let the user know that auth has succeeded!
    return "Auth complete!"

# main index of webpage https://drumpfbot.herokuapp.com
@app.route('/', methods=['GET'])
def test():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
