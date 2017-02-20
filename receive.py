# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests

import redis

app = Flask(__name__)

# bot = DrumpfBot()

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')

# SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN', None)
# slack_client = SlackClient(SLACK_TOKEN)

# r = redis.StrictRedis(host='localhost', port=5000, db=0)

# handles interactive button responses for donny_drumpfbot
@app.route('/actions', methods=['POST'])
def inbound():
    payload = request.form.get('payload')
    data = json.loads(payload)
    token = data['token']
    if token == SLACK_VERIFICATION_TOKEN:
        print 'TOKEN is good!'


        response_url = data['response_url']
        user_info = data['user']
        user_id = user_info['id']
        user_name = user_info['name']
        actions = data['actions'][0]
        value = actions['value']

        print 'User sending message: ',user_name
        print "value received: ",value
        # r.set('value',value)
        # r.set('user_id',user_id)
        DrumpfBot().receive_button_action(value,user_id)
    return Response(), 200


@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
