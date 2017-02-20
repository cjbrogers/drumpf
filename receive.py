import os
from flask import Flask, request, Response
from slackclient import SlackClient

app = Flask(__name__)

SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')

SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN', None)
slack_client = SlackClient(SLACK_TOKEN)

def send_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=message,
        username='pythonbot',
        icon_emoji=':robot_face:'
    )

@app.route('/actions', methods=['POST'])
def inbound():
    if request.form.get('token') == SLACK_WEBHOOK_SECRET:
        # channel = request.form.get('channel_name')
        # channel_id = request.form.get('channel_id')
        # username = request.form.get('user_name')
        # user_id = request.form.get('user_id')
        # text = request.form.get('text')
        # inbound_message = username + " in " + channel + " says: " + text
        # send_message(channel_id,inbound_message)
        # print(inbound_message)
        print(request.form)
    return Response(), 200


@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
