from __future__ import print_function
from __future__ import unicode_literals

from rtmbot.core import Plugin
# from drumpfbot import DrumpfBot



class RepeatPlugin(Plugin):

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

    def process_message(self, data):
        if data['channel'] == "C41Q1H4BD":
            if data['text'] == "trump selection":
                attachments =[{"title":"**TESTING**\nPlease select index for trump suit:", "fallback":"Your interface does not support interactive messages.", "callback_id":"prompt_trump_suit", "attachment_type":"default", "actions":[{"name":"diamonds","text":":diamonds:","type":"button","value":"0"},
                {"name":"clubs","text":":clubs:","type":"button","value":"1"},
                {"name":"hearts","text":":hearts:","type":"button","value":"2"},
                {"name":"spades","text":":spades:","type":"button","value":"3"}]}]
                self.slack_client.api_call(
                    "chat.postMessage",
                    channel=data['channel'],
                    as_user=True,
                    attachments=attachments
                )
                # self.outputs.append(
                #     [data['channel'], 'from user: "{}" plugin: "RepeatPlugin" command: "{}" in channel {}'.format(data['user'],
                #         data['text'], data['channel']
                #     )]
                # )
