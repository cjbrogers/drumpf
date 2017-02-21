# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests

import drumpfbot
import slackprovider
from slacker import Slacker

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')

slack_client = slackprovider.get_slack_client()
slack = Slacker(os.environ.get('SLACK_BOT_TOKEN'))

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
        drumpfbot.value = value
        drumpfbot.uid = user_id
        drumpfbot.receive_channel = channel_id

        print 'User sending message: ',user_name
        print "value received: ",value
        slack.chat.post_message(channel_id,"@donny_drumpfbot {}".format(value),user_name)
    return Response(), 200

@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
