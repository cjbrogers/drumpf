import os
from slackclient import SlackClient

def get_slack_client():
    slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
    return slack_client
