# -*- coding: utf-8 -*-
import os
import sys
import time
import copy
from slackclient import SlackClient
from collections import defaultdict, deque
from slacker import Slacker
import game as DrumpfGame
import helper_functions
import controller
import scoring
from scoring import Scoring
import bidding
from bidding import Bid
import round
from round import Round
import trump_suit
from trump_suit import TrumpSuit
import display_messages
from display_messages import DisplayMessages

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(helper_functions.get_slack_client())
slack = Slacker(helper_functions.get_slack_client())

class DrumpfBot():
    def __init__(self, main_channel_id='C4AK56EQ7'): # drumpf-scoreboard: C4AK56EQ7
        self.users_in_game = deque([]) #[user_id, user_id...]
        self.user_ids_to_username = {} #{'USERID': 'James'}
        self.channel_ids_to_name = {} #{'CHANNELID': "#drumpf-play"}
        self.main_channel_id = main_channel_id #TODO make this dynamic
        self.game_scorecard = defaultdict(int)

        self.player_trump_card_queue = [] #['USERID']
        self.player_bid_queue = [] #['USERID1', 'USERID2', 'USERID3']
        self.player_turn_queue = [] #['USERID1', 'USERID2', 'USERID3']
        self.player_turn_queue_reference = []
        self.dealer_for_current_round = None

        #ROUND VARIABLES
        self.player_bids_for_current_round = {} #{"U3LCLSTA5": 1, "U3MP47XAB": 0}
        self.current_game = None #DrumpfGame.Game() object
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None #string
        self.zero_point_players = [] #if users play blacks card in a sub round they get 0 points for that round
        self.shower_card_holder = [] # holds the player who holds the golden shower card

        #SUB-ROUND VARIABLES
        self.cards_played_for_sub_round = [] #this mirrors player_turn_queue as to determine a winner
        self.winner_for_sub_round = None
        self.sub_rounds_played = 0
        self.winning_sub_round_card = None

        self.attachments = None
        self.game_started = False
        self.game_created = False
        self.vm_cards = ["vm_blacks","vm_hombres","vm_thieves","vm_muslims"]
        self.t_cards = ["t_comey","t_nasty","t_russian","t_shower"]
        self.d_cards = ["d_wall","d_clinton","d_ivanka","d_pussy"]
        self.drumpfmendous_card_first = None
        self.first_card_sub_round = 0
        self.dealer_prompted_for_trump_suit = False
        self.scoreboard = ""
        self.ts = ""
        self.scores = ""
        self.initial_scores = ""
        self.command_ts = ""
        self.winning_points = None

    def handle_command(self, command, channel, user_id, ts):
        """
        Takes incoming command from the websocket, along with the user id, channel and timestamp and performs actions based on the command
        Args:
            [command] (str) the command to be executed
            [channel] (str) the channel id that the message originated from
            [user_id] (str) the id of the user sending the message
            [ts] (str) the timestamp of the incoming message
        Returns:
        """
        print "handle_command(self, command, channel, user_id, ts) "
        print "  command: ", command
        print "  channel: ", channel
        print "  user_id: ", user_id
        print "  player: ", self.user_ids_to_username[user_id]

        attachments = None
        username = self.user_ids_to_username[user_id] #user who sent the message

        response = "Wrong! Bing-bing-bing! Try `@drumpfbot help` for a tremendous list of available commands."

        if command.lower().startswith("debug"):
            if command.lower().startswith("debug 500"):
                self.winning_points = 500
            if command.lower().startswith("debug 1000"):
                self.winning_points = 1000
            # response = "`Debug mode active.` \n"
            # slack_client.api_call("chat.postMessage", channel=channel,
            #                       text=response, as_user=True)
            self.game_created == True
            self.users_in_game.append(user_id)
            self.users_in_game.append('U44V02PDY') #Roberto U3LCLSTA5 Alex U3LNCN0F3 Gordi-bot U42H6H9L5 Slackbot USLACKBOT drumpfbot U41R44L82 Cam U3N36HRHU James U3MP47XAB Test Icle U44V02PDY
            response = ""
            self.handle_command("start game", channel, user_id, ts)

        if command.lower().startswith("create game"):
            if command.lower().startswith("create game 500"):
                self.winning_points = 500
            if command.lower().startswith("create game 1000"):
                self.winning_points = 1000
            self.game_created == True
            if len(self.users_in_game) == 0:
                response = "<@{}> Wants to play a game of drumpf! Type `@drumpfbot add me` to play.".format(username)
                self.users_in_game.append(user_id)
            else:
                response = "There's already a game being made, say `@drumpfbot add me` if you want in."
            self.ts = ts

        if command.lower().startswith("restart"):
            response = "Application restarted."
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text=response, as_user=True, attachments=attachments)
            return self.restart_program()

        if command.lower().startswith("remove me") and (self.game_started == False) and (self.game_created == True):
            if user_id not in self.users_in_game:
                response = "You haven't been added, so how can I remove you? Type `@drumpfbot add me` if you want in."
            else:
                response = "Okay, {} removed from the game queue. When you have two or more players, type `@drumpfbot start game`.".format(username)
                self.users_in_game.remove(user_id)

        if command.lower().startswith("add me"):
            if len(self.users_in_game) == 0:
                response = "There is no active game, try `create game`."
            else:
                if user_id in self.users_in_game:
                    response = "You've already been added to the game."
                else:
                    self.users_in_game.append(user_id)
                    response = "Added <@{}> to the game!".format(username)
                    response += "\n_We're good to go! Type `@drumpfbot start game` to get your Drumpf on._"

        if command.lower().startswith("start game"):
            print "Users in game: ", self.users_in_game
            if len(self.users_in_game) == 0:
                response = "No game exists yet. Try `@drumpfbot create game`"
            elif len(self.users_in_game) < 2:
                response = "There aren't enough players yet (minimum 2). Users can say `add me` to be added to the game."
            elif len(self.users_in_game) > 6:
                response = "There are too many players (max 6). Please try again."
            else:
                self.game_started = True
                response = ">>>Starting a new game of Drumpf!\n"

                score.initialize_scores()

                resp = slack_client.api_call("chat.postMessage", channel=channel,text=response,as_user=True)
                self.ts = resp['ts']
                self.play_game_of_drumpf_on_slack(self.users_in_game, channel)
                return

        if command.lower().startswith("commands") or command.lower().startswith("help"):
            response = ">>>Certainly, my liege. The available commands are: \n\n" \
            "*[add me]*\tAdd yourself to the game queue.\n" \
            "*[bigly]*\tIt's a word.\n" \
            "*[cancel]*\tStop the current game.\n" \
            "*[commands]*\tView available commands.\n" \
            "*[comp]*\tView the card deck composition.\n" \
            "*[create game]*\tLet Slack know you want to play a game. Players reply '<@drumpfbot> add me' if they wish to join.\n"\
            "*[debug]*\tStart a game in debug mode. Bidding is automatic.\n" \
            "*[remove me]*\tRemove yourself from the current game queue.\n" \
            "*[rules]*\tView the rules of the game.\n" \
            "*[start game]*\tStart the game.\n" \
            "*[undebug]*\tTurn off the debugging output.\n" \
            "*[< _these_ > cards]*\tReplace < _these_ > with the cards you wish to view. i.e. 'Drumpf' cards.\n\n" \
            "Still lost? Follow this link for step-by-step instructions:"
            title_link = "http://cjbrogers.com/drumpf/howto.html"
            attachments = [{"title": "@drumpfbot How To Reference - Click here to learn more", "title_link": title_link}]

        if command.lower().startswith("rules") or command.lower().startswith("game rules"):
            response = ">>>Right away, master. Here are the rules: \n\n"
            title_link = "http://cjbrogers.com/drumpf/DrumpfGameDesign.html"
            attachments = [{"title": "DRUMPF! The Rules - Click here to learn more", "title_link": title_link}]

        if command.lower().startswith("bigly"):
            response = ">>>*bigly* (ˈbɪɡlɪ) \n_adj_\n\t\t_archaic_ comfortably habitable"

        if command.lower().startswith("what's a joker?"):
            response = ">>>This is: \n"
            image_url = "https://s29.postimg.org/9ide0xa0n/joker.png"
            attachments = [{"title": "The Joker", "image_url": image_url}]

        if command.lower().startswith("visible minority cards"):
            response = ">>>Racism is bad. \n"
            image_url = "https://s27.postimg.org/8ffx0pigz/vmcards.png"
            attachments = [{"title": "Visible Minority Cards", "image_url": image_url}]

        if command.lower().startswith("tremendous cards"):
            response = ">>>Your wish is my command: \n"
            image_url = "https://s23.postimg.org/6hntc9lej/tcards.png"
            attachments = [{"title": "Tremendous Cards", "image_url": image_url}]

        if command.lower().startswith("drumpf cards"):
            response = ">>>At your service, you sexy thing you: \n"
            image_url = "https://s24.postimg.org/4jwyhuj2d/dcards.png"
            attachments = [{"title": "Drumpf Cards", "image_url": image_url}]

        if command.lower().startswith("comp"):
            response = ">>>Here's the card deck composition: \n"
            image_url = "https://s30.postimg.org/r28wxm89t/cards.png"
            attachments = [{"title": "Card Deck Composition", "image_url": image_url}]

        resp = slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True, attachments=attachments)

    def play_game_of_drumpf_on_slack(self, players, channel):
        """Takes an array of player_ids and the channel the game request originated from

        Args:
            [players] (list(Player())) a list of the player objects in game
            [channel] (str) the channel
        Returns:
        """
        print "play_game_of_drumpf_on_slack(self, players, channel) "
        print "  players: ", players
        print "  channel: ", channel

        player_objects = []
        for player_id in players:
            player_objects.append(DrumpfGame.Player(player_id))
        game = DrumpfGame.Game(player_objects, self, bid)
        game.play_round()

    def prepare_for_next_round(self):
        """Clears all round and sub-round variables

        Args:
        Returns:
        """
        print "prepare_for_next_round(self) "
        self.bot.current_game.current_round += 1
        self.bot.scoreboard = ""
        self.bot.scores = ""
        for k in self.bot.player_bids_for_current_round.keys():
            self.bot.player_bids_for_current_round[k] = ""
        self.bot.player_points_for_round = defaultdict(int)
        self.bot.leading_suit = None
        self.bot.sub_rounds_played = 0
        self.bot.winning_sub_round_card = None
        self.bot.winner_for_sub_round = None
        self.bot.cards_played_for_sub_round = []
        self.bot.zero_point_players = []
        self.bot.shower_card_holder = []
        self.bot.drumpfmendous_card_first = None
        self.bot.player_bid_queue.clear()
        self.bot.current_game.current_round_trump_suit = None
        self.bot.first_card_sub_round = 0
        self.bot.player_turn_queue.rotate(1)

    def restart_program(self):
        """
            Restarts the current program.
        """
        print "restart_program(self)"
        python = sys.executable
        os.execl(python, python, * sys.argv)

    def parse_slack_output(self):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = slack_client.rtm_read()
        if output_list and len(output_list) > 0:
            print output_list
            for output in output_list:
                if output and 'text' in output and AT_BOT in output['text']:
                    # return text after the @ mention, whitespace removed
                    #example return: (u'hi', u'C2F154UTE', )
                    if 'ts' in output:
                        return output['text'].split(AT_BOT)[1].strip().lower(), output['channel'], output['user'], output['ts']
                    else:
                        return output['text'].split(AT_BOT)[1].strip().lower(), output['channel'], output['user'], None
        return None, None, None, None

    def main(self):
        """
            Opens a Slack RTM API websocket connection
        """
        READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
        #grab user list and converts it to to a dict of ids to usernames
        api_call = slack_client.api_call("users.list")

        if api_call.get('ok'):
            users = api_call.get('members')
            for user in users:
                self.user_ids_to_username[user['id']] = user['name']

            channels = slack_client.api_call("channels.list").get('channels')
            for channel in channels:
                self.channel_ids_to_name[channel['id']] = channel['name']

        if slack_client.rtm_connect():
            print("DRUMPFBOT v1.0 connected and running!")

            while True:
                command, channel, user, ts = self.parse_slack_output()
                if command and channel:
                    if channel not in self.channel_ids_to_name.keys():
                        #this (most likely) means that this channel is a PM with the bot
                        self.handle_private_message(command, user)
                    else:
                        self.handle_command(command, channel, user, ts)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")

if __name__ == "__main__":
    bot = DrumpfBot()
    score = Scoring(bot)
    trump = TrumpSuit(bot,score)
    round_ = Round(bot,score)
    bid = Bid(bot,score)
    dm = DisplayMessages(bot,bid,trump,round_)
    bot.main()
