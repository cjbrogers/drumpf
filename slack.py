import os
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, redirect, url_for, request
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_sslify import SSLify
from raven.contrib.flask import Sentry

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

@app.route("/actions/", methods=['POST'])
def actions():
    app.slack_client.rtm_send_message("drumpf-play", "I'm ALIVE!!!")
    attachments =[{"title":"TESTING Please select index for trump suit:", "fallback":"Your interface does not support interactive messages.", "callback_id":"prompt_trump_suit", "attachment_type":"default", "actions":[{"name":"diamonds","text":":diamonds:","type":"button","value":"0"},
    {"name":"clubs","text":":clubs:","type":"button","value":"1"},
    {"name":"hearts","text":":hearts:","type":"button","value":"2"},
    {"name":"spades","text":":spades:","type":"button","value":"3"}]}]
    app.slack_client.api_call(
        "chat.postMessage",
        channel=request.form['user'],
        text="please select index for trump suit \n `0`[:diamonds:]   `1`[:clubs:]   `2`[:hearts:]   `3`[:spades:]",
        as_user=True,
        attachments=attachments
    )

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
