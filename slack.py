from __future__ import unicode_literals
import os
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, redirect, url_for, request
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_sslify import SSLify
from raven.contrib.flask import Sentry
import requests

from slackclient import SlackClient

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
sentry = Sentry(app)
sslify = SSLify(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get("SLACK_OAUTH_CLIENT_ID")
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get("SLACK_OAUTH_CLIENT_SECRET")
slack_bp = make_slack_blueprint(scope=["identify", "chat:write:bot"])
app.register_blueprint(slack_bp, url_prefix="/login")

app.slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
app.api_call = app.slack_client.api_call("users.list")
app.slack_client.rtm_connect()

@app.route("/responses/", methods=['POST'])
def responses():
    print request.get_json()
    payload={"text": "bananas"}
    requests.post("https://hooks.slack.com/services/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",json=payload)

@app.route("/actions/", methods=['POST'])
def actions():
    payload={"text": "A very important thing has occurred! <https://alert-system.com/alerts/1234|Click here> for details!"}
    requests.post("https://hooks.slack.com/services/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",json=payload)

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
