from __future__ import unicode_literals
import os
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, redirect, url_for, request
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_sslify import SSLify
from raven.contrib.flask import Sentry
import requests

from slackclient import SlackClient

import drumpfbot
from drumpfbot import DrumpfBot

class FlaskApp(Flask):

   def __init__(self, *args, **kwargs):
       super(FlaskApp, self).__init__(*args, **kwargs)
       self.bot = DrumpfBot()
       self.bot.main()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
sentry = Sentry(app)
sslify = SSLify(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get("SLACK_OAUTH_CLIENT_ID")
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get("SLACK_OAUTH_CLIENT_SECRET")
slack_bp = make_slack_blueprint(scope=["identify", "chat:write:bot"])
app.register_blueprint(slack_bp, url_prefix="/login")

# app.slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# app.api_call = app.slack_client.api_call("users.list")
# app.slack_client.rtm_connect()

slack_client = drumpfbot.slack_client

@app.route("/responses/", methods=['POST'])
def responses():
    print request.get_json()
    slack_client.api_call(
        "chat.postMessage",
        channel="C41Q1H4BD",
        text="alex",
        as_user=True
    )
    return "OK"

@app.route("/actions/", methods=['POST'])
def actions():
    print request.get_json()
    slack_client.api_call(
        "chat.postMessage",
        channel="C41Q1H4BD",
        text="james",
        as_user=True
    )
    return "OK"

@app.route("/")
def index():
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    resp = slack.post("chat.postMessage", data={
        "channel": "#drumpf-play",
        "text": "ping",
        "icon_emoji": ":robot_face:",
    })
    assert resp.ok, resp.text
    return resp.text

if __name__ == "__main__":
    app.run(debug=True)
