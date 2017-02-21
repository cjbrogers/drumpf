import os

def get_slack_client():
    token = os.environ.get('SLACK_BOT_TOKEN')
    return token
