# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response, render_template
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests
from slacker import Slacker
import pandas as pd
import giphypop
import random

import app
from app import tasks
import models


SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')
CLIENT_ID = os.environ["SLACK_OAUTH_CLIENT_ID"]
CLIENT_SECRET = os.environ["SLACK_OAUTH_CLIENT_SECRET"]
OAUTH_SCOPE = os.environ["SLACK_BOT_SCOPE"]

app = Flask(__name__)
g = giphypop.Giphy()

# handles interactive button responses for donny_drumpfbot
@app.route('/actions', methods=['POST'])
def inbound():

    payload = request.form.get('payload')
    data = json.loads(payload)
    token = data['token']
    # if token == SLACK_VERIFICATION_TOKEN:
        # print '  TOKEN is good!'
        # print data
    response_url = data['response_url']
    channel_info = data['channel']
    channel_id = channel_info['id']
    user_info = data['user']
    user_id = user_info['id']
    user_name = user_info['name']
    team_info = data['team']
    team_id = team_info['id']
    actions = data['actions'][0]
    value = actions['value']
    print "  Channel ID: ",channel_id
    print "  Team ID: ",team_id
    print '  User sending message: ',user_name
    print "  Value received: ",value

    access_token = models.get_access_token(user_id)
    slack_client = SlackClient(access_token)
    bot_access_token = models.get_bot_access_token(user_id)
    # for token in tokens:
    try:
        BOT_ID = models.get_bot_user_id(bot_access_token)
        AT_BOT = "<@" + BOT_ID + ">"
        if value == "screw off":
            urls = [x for x in g.search(value)]
            random.shuffle(urls)
            print "  urls:",urls
            url = urls[0]
            print "  url:",url
            image_url = url.media_url
            print "  image_url:",image_url
            sql = "SELECT ts FROM `messages` WHERE event='rules' AND team_id='{}'".format(team_id)
            engine = models.get_engine()
            df = pd.read_sql_query(sql=sql,con=engine)
            ts = df.iloc[0]['ts']
            print "  ts:",ts
            attachments = [
                {
                    "title": "Just wanted to say screw off.",
                    "fallback": "Screw off.",
                    "author_name": user_name,
                    "color": "#36a64f",
                    "pretext": "ALERT!",
                    "image_url": image_url
                }]
            resp = slack_client.api_call("chat.update",
                                        channel=channel_id,
                                        text = "",
                                        ts=ts,
                                        attachments=attachments,
                                        as_user=True)
        else:
            resp = slack_client.api_call("chat.postMessage",
                                        channel=channel_id,
                                        text = AT_BOT +" {}".format(value),
                                        as_user=True)
            if resp['ts']:
                ts = resp['ts']
                slack_client.api_call("chat.delete", channel=channel_id,ts=ts,as_user=True)

    except:
        print "  unsuccessful token retrieval attempt"
    else:
        print "  successful token retrieval"

    return Response(), 200

# handles interactive button responses for donny_drumpfbot
@app.route('/events', methods=['POST'])
def events():
    data = json.loads(request.data)
    print data
    # token = data['token']
    # if token == SLACK_VERIFICATION_TOKEN:
    try:
        for k,v in data['event'].iteritems():
            if 'previous_message' not in str(k) and ('play drumpf' in str(v) or 'restart' in str(v)):
                ts = data['event']['ts']
                channel = data['event']['channel']
                user_id = data['event']['user']
                team_id = data['team_id']
                msg = data['event']['text']
                try:
                    access_token = models.get_access_token(user_id)
                    slack_client = SlackClient(access_token)
                    resp = slack_client.api_call("chat.delete", channel=channel,ts=ts,as_user=True)
                except:
                    print "  no token available for call..."
                else:
                    print "  successful deletion of 'play drumpf / restart' user command"
                if 'play drumpf' in str(v):
                    tasks.launch_bot.delay(user_id,channel,ts,team_id)
                    return Response(), 200
            elif 'previous_message' not in str(k) and 'wake donny_drumpfbot' in str(v):
                print "  waking up Drumpf!"
                ts = data['event']['ts']
                channel = data['event']['channel']
                user_id = data['event']['user']
                team_id = data['team_id']

                user_access_token = models.get_access_token(user_id)
                slack_client = SlackClient(user_access_token)
                slack_client.api_call("chat.delete", channel=channel,ts=ts,as_user=True)

                bot_access_token = models.get_bot_access_token(user_id)
                slack_client = SlackClient(bot_access_token)

                response = ""
                title_link = "http://cjbrogers.com/drumpf/DrumpfGameDesign.html"
                attachments = [
                    {
                        "title": "DRUMPF! The Rules - Click here to learn more",
                        "color": "#FB8C00",
                        "title_link": title_link
                    }]

                resp = slack_client.api_call("chat.postMessage",
                                                  channel=channel,
                                                  text=response,
                                                  attachments=attachments,
                                                  as_user=True)
                rules_ts = resp['ts']
                event = "rules"
                models.log_message_ts(rules_ts,channel,event,team_id)

                message = "You have successfully drawn <@donny_drumpfbot>'s attention away from Twitter, at least for the time being."
                attachments = [
                {
                    "title":"It's time to start lying and cheating your way to a TREMENDOUS victory!",
                    "fallback":"Play a game of Drumpf.",
                    "color": "#3AA3E3",
                    "callback_id":"play_drumpf",
                    "attachment_type":"default",
                    "actions": [
                        {
                            "name":"play drumpf",
                            "text":"play drumpf",
                            "style":"primary",
                            "type":"button",
                            "value":"play drumpf"
                        }
                    ]
                }]

                resp = slack_client.api_call("chat.postMessage",
                                             text=message,
                                             channel=channel,
                                             attachments=attachments,
                                             as_user=True)
                ts_wake = resp['ts']
                team_id = data['team_id']
                event = "wake_bot"
                models.log_message_ts(ts_wake,channel,event,team_id)
                return Response(), 200
    except Exception as e:
        raise
    else:
        print "  Event successfully registered."
    return Response(), 200

# the beginning of the Sign In to Slack OAuth process.
# we can get the user tokens from the return of this call
@app.route("/signin", methods=["GET"])
def pre_signin():
    redirect_uri1 = "https://drumpfbot.herokuapp.com/signin/finish"
    redirect_uri2 = "https://drumpfbot.herokuapp.com/auth/finish"
    return render_template("slack.html", redirect_uri1=redirect_uri1,redirect_uri2=redirect_uri2,OAUTH_SCOPE=OAUTH_SCOPE,CLIENT_ID=CLIENT_ID)

# end of the Slack signin process, appending relevant user information including tokens into the db
@app.route("/signin/finish", methods=["GET", "POST"])
def post_signin():
    redirect_uri = "https://drumpfbot.herokuapp.com/signin/finish"
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
    access_token = auth_response['access_token']
    user_id = auth_response['user_id']
    team_id = auth_response['team_id']
    team_name = auth_response['team_name']
    bot_access_token = auth_response['bot']['bot_access_token']
    bot_user_id = auth_response['bot']['bot_user_id']
    name = ""

    values = {"user_id": user_id, "name": name, "access_token": access_token,"bot_access_token": bot_access_token, "bot_user_id": bot_user_id, "team_id": team_id, "team_name": team_name}
    df = pd.DataFrame(values, index=[0])
    engine = models.get_engine()
    models.send_to_db(df,engine,'users')

    # Don't forget to let the user know that auth has succeeded!
    return "<h1>Welcome to Drumpf! on Slack!</h1> You can now <a href='https://drumpfbot.herokuapp.com/'>head back to the main page</a>, or just close this window."

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
        # redirect_uri=redirect_uri,
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
    engine = models.get_engine()
    models.send_to_db(df,engine,'team')
    return "Auth complete!"

# main index of webpage https://drumpfbot.herokuapp.com
@app.route('/', methods=['GET'])
def index():
    redirect_uri1 = "https://drumpfbot.herokuapp.com/signin/finish"
    redirect_uri2 = "https://drumpfbot.herokuapp.com/auth/finish"
    return render_template('index.html',redirect_uri1=redirect_uri1,redirect_uri2=redirect_uri2,OAUTH_SCOPE=OAUTH_SCOPE,CLIENT_ID=CLIENT_ID)

if __name__ == "__main__":
    app.run(debug=True)
