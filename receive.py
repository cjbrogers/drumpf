# -*- coding: utf-8 -*-
import os
from flask import Flask, request, Response
from slackclient import SlackClient
from werkzeug.datastructures import ImmutableMultiDict
import json, requests

from drumpfbot import DrumpfBot

app = Flask(__name__)

# bot = DrumpfBot()

SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')


class Bot:
    def __init__(self):
        self.bot = DrumpfBot()
        self.bot.main()

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
        app.bot.receive_button_action(value,user_id)
    return Response(), 200

@app.route('/start', methods=['POST'])
def start():
    bot = Bot()
    return bot

@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
