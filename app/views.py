# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response, render_template
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests
from slacker import Slacker
import pandas as pd

from celery import Celery

import models
import bot
from bot import DrumpfBot
import scoring
from scoring import Scoring
import bidding
from bidding import Bid
import round
from round import Round
import trump_suit
from trump_suit import TrumpSuit

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')
CLIENT_ID = os.environ["SLACK_OAUTH_CLIENT_ID"]
CLIENT_SECRET = os.environ["SLACK_OAUTH_CLIENT_SECRET"]
OAUTH_SCOPE = os.environ["SLACK_BOT_SCOPE"]

app = Flask(__name__)

def make_celery(app):
    celery = Celery(app.name, broker=os.environ.get('RABBITMQ_BIGWIG_URL'))
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self,*args,**kwargs):
            with app.app_context():
                return TaskBase.__call__(self,*args,**kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

@celery.task
def launch_bot(user_id,channel):
    bot = DrumpfBot()
    bot.initialize(user_id, channel)
    score = Scoring(bot, user_id)
    bid = Bid(bot,score)
    trump = TrumpSuit(bot,score,bid)
    round_ = Round(bot,score,trump)
    bot.main(score, bid, trump, round_)

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
    actions = data['actions'][0]
    value = actions['value']
    print "  Channel ID: ",channel_id
    print '  User sending message: ',user_name
    print "  Value received: ",value

    access_token = models.get_access_token(user_id)
    slack_client = SlackClient(access_token)
    bot_access_token = models.get_bot_access_token(user_id)
    # for token in tokens:
    try:
        BOT_ID = models.get_bot_user_id(bot_access_token)
        AT_BOT = "<@" + BOT_ID + ">"
        resp = slack_client.api_call("chat.postMessage",channel=channel_id,text = AT_BOT +" {}".format(value),as_user=True)
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
            if 'previous_message' not in str(k) and 'create game' in str(v):
                ts = data['event']['ts']
                channel = data['event']['channel']
                user_id = data['event']['user']
                access_token = models.get_access_token(user_id)
                try:
                    slack_client = SlackClient(access_token)
                    resp = slack_client.api_call("chat.delete", channel=channel,ts=ts,as_user=True)
                except:
                    print "  create game not in data['event']['text']"
                else:
                    print "  successful bot initialization"
                    launch_bot.delay(user_id,channel)
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
