from __future__ import print_function
from __future__ import unicode_literals
from site-packages import rtmbot.core.Plugin

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

class MyPlugin(Plugin):

    def catch_all(self, data):
        print("catch_all(self,data)")
        print(data)
