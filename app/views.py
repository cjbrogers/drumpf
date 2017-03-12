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

suits = ["diamonds", "clubs", "hearts", "spades"]

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
    name = actions['name']
    print "  Channel ID: ",channel_id
    print "  Team ID: ",team_id
    print '  User sending message: ',user_name
    print "  Value received: ",value
    print "  Name received: ",name


    bot_access_token = models.get_bot_access_token(user_id)
    # for token in tokens:
    try:
        if value == "gif":
            screw_terms = ["screw off","screw you","piss off","fuck off","fuck you","damn you","you suck"]
            dammit_terms = ["god dammit", "dammit", "damn it", "gosh darnit", "damn you"]
            cry_terms = ["don't cry", "stop crying", "cry baby", "boo hoo", "so sad"]
            sucka_terms = ["sucka", "nice try sucka", "nice try", "better luck next time","you lose"]
            search_terms = {"screw you":screw_terms, "dammit":dammit_terms, "don't cry":cry_terms, "sucka":sucka_terms}

            terms = []
            image_url = ""
            print "  actions:",actions
            if name in search_terms.keys(): # the button clicked is a search term
                terms = search_terms[name]
                print "  terms:",terms
                random.shuffle(terms)
                term = terms[0]
                print "  SEARCH TERM:",term

                urls = [x for x in g.search(term)]
                random.shuffle(urls)
                url = urls[0]
                image_url = url.media_url
                print "  urls:",urls
                print "  url:",url
                print "  image_url:",image_url
            else: # just get a random gif
                image_urls = ["https://media.giphy.com/media/ytwDCq9aT3cgEyyYVO/giphy.gif",
                "https://media.giphy.com/media/YTbZzCkRQCEJa/giphy.gif",
                "https://media.giphy.com/media/jMBmFMAwbA3mg/giphy.gif",
                "https://media.giphy.com/media/l0MYxef0mpdcnQnvi/source.gif",
                "https://media.giphy.com/media/3o7TKtsBMu4xzIV808/giphy.gif",
                "https://media.giphy.com/media/l3q2Z6S6n38zjPswo/giphy.gif",
                "https://media.giphy.com/media/kmqCVSHi5phMk/giphy.gif",
                "https://media.giphy.com/media/9X5zV9eHAqAus/giphy.gif",
                "https://media.giphy.com/media/Xv0Y0A2GsrZ3G/giphy.gif"]
                random.shuffle(image_urls)
                image_url = image_urls[0]

            ts = models.get_ts(channel_id,"rules",team_id)
            print "  ts:",ts
            attachments = [
                {
                    "title": user_name + " says \"" +name+ "\"",
                    "fallback": "Gifs",
                    "callback_id":"rules_gifs",
                    "color": "#FB8C00",
                    "image_url": image_url,
                    "actions": [
                        {
                            "name":"screw you",
                            "text":"screw you",
                            "style":"danger",
                            "type":"button",
                            "value":"gif"
                        },
                        {
                            "name":"don't cry",
                            "text":"don't cry",
                            "style":"primary",
                            "type":"button",
                            "value":"gif"
                        },
                        {
                            "name":"dammit",
                            "text":"dammit",
                            "style":"danger",
                            "type":"button",
                            "value":"gif"
                        },
                        {
                            "name":"sucka",
                            "text":"sucka",
                            "style":"primary",
                            "type":"button",
                            "value":"gif"
                        }
                    ]
                }]
            slack_client = SlackClient(bot_access_token)
            resp = slack_client.api_call("chat.update",
                                        channel=channel_id,
                                        text = "",
                                        ts=ts,
                                        attachments=attachments,
                                        as_user=True)
        elif name[0:3] == "bid":
            # no_button_sets = int(name[-1])
            # print "  no_button_sets:",no_button_sets

            slack_client = SlackClient(bot_access_token)
            bot_im_id = models.get_bot_im_id(user_id,team_id)

            connection = models.connect()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT ts FROM `messages` WHERE event LIKE %s AND team_id=%s AND channel=%s"
                    event = "bid_buttons%"
                    data = (event,team_id,bot_im_id)
                    cursor.execute(sql,data)
                    timestamps = cursor.fetchall()
                    for timestamp in timestamps:
                        print timestamp['ts']
                        slack_client.api_call("chat.delete",
                                            channel=bot_im_id,
                                            ts=timestamp['ts'],
                                            as_user=True)
            except Exception as e:
                raise
            else:
                print "  Great success!"
            finally:
                connection.close()
            # for i in range(1,(no_button_sets+1)):
            #     print str(i)
            #     ts = models.get_ts(bot_im_id,"bid_buttons_{}".format(str(i)),team_id)
            #     slack_client.api_call("chat.delete",
            #                             channel=bot_im_id,
            #                             ts=ts,
            #                             as_user=True)

            access_token = models.get_access_token(user_id)
            slack_client = SlackClient(access_token)
            BOT_ID = models.get_bot_user_id(bot_access_token)
            AT_BOT = "<@" + BOT_ID + ">"
            resp = slack_client.api_call("chat.postMessage",
                                        channel=channel_id,
                                        text = AT_BOT +" {}".format(value),
                                        as_user=True)
            if resp['ts']:
                ts = resp['ts']
                slack_client.api_call("chat.delete", channel=channel_id,ts=ts,as_user=True)
        elif name[0:9] == "play_card":
            slack_client = SlackClient(bot_access_token)
            bot_im_id = models.get_bot_im_id(user_id,team_id)
            event = "init_cards_pm_" + name[-1]
            ts = models.get_ts(bot_im_id,event,team_id)

            attachments = [
                {
                    "title": "Waiting on other players...",
                    "fallback": "card played",
                    "color": "#9E9E9E",
                    "callback_id":"interactify",
                }]

            slack_client.api_call("chat.update",
                                    channel=bot_im_id,
                                    ts=ts,
                                    text=":white_check_mark:",
                                    attachments=attachments,
                                    as_user=True)

            access_token = models.get_access_token(user_id)
            slack_client = SlackClient(access_token)
            BOT_ID = models.get_bot_user_id(bot_access_token)
            AT_BOT = "<@" + BOT_ID + ">"
            resp = slack_client.api_call("chat.postMessage",
                                        channel=channel_id,
                                        text = AT_BOT +" {}".format(value),
                                        as_user=True)
            if resp['ts']:
                ts = resp['ts']
                slack_client.api_call("chat.delete", channel=channel_id,ts=ts,as_user=True)
        elif name in suits:
            slack_client = SlackClient(bot_access_token)
            bot_im_id = models.get_bot_im_id(user_id,team_id)
            event = "trump_suit"
            ts = models.get_ts(bot_im_id,event,team_id)

            slack_client.api_call("chat.delete", channel=bot_im_id,ts=ts,as_user=True)

            access_token = models.get_access_token(user_id)
            slack_client = SlackClient(access_token)
            BOT_ID = models.get_bot_user_id(bot_access_token)
            AT_BOT = "<@" + BOT_ID + ">"
            resp = slack_client.api_call("chat.postMessage",
                                        channel=channel_id,
                                        text = AT_BOT +" {}".format(value),
                                        as_user=True)
            if resp['ts']:
                ts = resp['ts']
                slack_client.api_call("chat.delete", channel=channel_id,ts=ts,as_user=True)
        else:
            access_token = models.get_access_token(user_id)
            slack_client = SlackClient(access_token)
            BOT_ID = models.get_bot_user_id(bot_access_token)
            AT_BOT = "<@" + BOT_ID + ">"
            resp = slack_client.api_call("chat.postMessage",
                                        channel=channel_id,
                                        text = AT_BOT +" {}".format(value),
                                        as_user=True)
            if resp['ts']:
                ts = resp['ts']
                slack_client.api_call("chat.delete", channel=channel_id,ts=ts,as_user=True)

    except Exception as e:
        raise
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
                        "callback_id":"rules_gifs",
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
    im_id = ""

    values = {"user_id": user_id, "name": name, "access_token": access_token,"bot_access_token": bot_access_token, "bot_user_id": bot_user_id, "team_id": team_id, "team_name": team_name, "bot_im_id": im_id}
    df = pd.DataFrame(values, index=[0])
    engine = models.get_engine()
    models.send_to_db(df,engine,'users')

    slack_client = SlackClient(access_token)
    ims = slack_client.api_call("im.list").get('ims')
    print "  IMS:",ims
    for im in ims:
        if im['user'] == bot_user_id:
            im_id = im['id']
            connection = models.connect()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE `users` SET bot_im_id=%s WHERE user_id=%s AND team_id=%s"
                    data = (im_id,user_id,team_id)
                    cursor.execute(sql,data)
            except Exception as e:
                raise
            else:
                print "  Successfully updated bot_im_id in users table."
            finally:
                connection.close()
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
