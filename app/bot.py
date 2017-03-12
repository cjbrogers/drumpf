# -*- coding: utf-8 -*-
import os
import sys
import time
from collections import defaultdict, deque
import pandas as pd
from slackclient import SlackClient
from slacker import Slacker

import models
import game as DrumpfGame
import helper_functions
import scoring
from scoring import Scoring
import bidding
from bidding import Bid
import round
from round import Round
import trump_suit
from trump_suit import TrumpSuit

class DrumpfBot():

    def __init__(self): # drumpf-scoreboard: C4AK56EQ7
        self.BOT_ID = ""
        self.AT_BOT = ""
        self.BOT_TOKEN = ""
        self.slack_client = None
        self.slack = None
        self.users_in_game = deque([]) #[user_id, user_id...]
        self.user_ids_to_username = {} #{'USERID': 'James'}
        self.channel_ids_to_name = {} #{'CHANNELID': "#drumpf-play"}
        self.main_channel_id = ""
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
        self.add_me_ts = ""
        self.scores = ""
        self.initial_scores = ""
        self.command_ts = ""
        self.winning_points = None
        self.team_id = ""
        # self.timestamps = {}

    def handle_command(self, command, channel, user_id, ts):
        """
        Takes incoming command from the websocket, along with the user id, channel and timestamp and performs actions based on the command

        Args:
            [command] (str) the command to be executed
            [channel] (str) the channel id that the message originated from
            [user_id] (str) the id of the user sending the message
            [ts] (str) the timestamp of the incoming message
        """
        print "handle_command(self, command, channel, user_id, ts) "
        print "  command: ", command
        print "  channel: ", channel
        print "  user_id: ", user_id
        print "  player: ", self.user_ids_to_username[user_id]
        team_id = models.get_team_id(user_id)
        print "  team_id: ",team_id

        attachments = None
        username = self.user_ids_to_username[user_id] #user who sent the message

        response = "Wrong! Bing-bing-bing! Try `@drumpfbot help` for a tremendous list of available commands."

        if command.lower().startswith("debug"):
            if command.lower().startswith("debug 100"):
                self.winning_points = 100
            if command.lower().startswith("debug 500"):
                self.winning_points = 500
            if command.lower().startswith("debug 1000"):
                self.winning_points = 1000
            self.game_created == True
            self.users_in_game.append(user_id)
            self.users_in_game.append('U44V02PDY') #Roberto U3LCLSTA5 Alex U3LNCN0F3 donny_drumpfbot U41R44L82 Cam U3N36HRHU James U3MP47XAB Testicle U44V02PDY
            self.slack_client.api_call("chat.delete", channel=channel,ts=ts,as_user=True)
            self.handle_command("start game", channel, user_id, ts)
            return

        if command.lower().startswith("create game"):
            if command.lower().startswith("create game 250"):
                self.winning_points = 250
            if command.lower().startswith("create game 500"):
                self.winning_points = 500
            if command.lower().startswith("create game 1000"):
                self.winning_points = 1000
            self.game_created == True
            self.slack_client.api_call("chat.delete", channel=channel,ts=ts,as_user=True)
            if len(self.users_in_game) == 0:
                response = "`Playing "
                if self.winning_points:
                    response += "to " + str(self.winning_points) + " points`"
                else:
                    response += "Standard Gameplay (play until the cards are all used)`"

                self.users_in_game.append(user_id)

                resp = self.slack_client.api_call("chat.postMessage", channel=channel,text=response,as_user=True)
                game_play_ts = resp['ts']
                event = "game_play"
                models.log_message_ts(game_play_ts,channel,event,team_id)

                response = "Hey there team! <@{}> wants to play a game of drumpf!".format(username)
                attachments = [
                    {
                        "title":"Feel free to add yourself to the game queue:",
                        "fallback":"Add me to the game:",
                        "callback_id":"add me",
                        "color": "#673AB7",
                        "attachment_type":"default",
                        "actions": [
                            {
                                "name":"add me",
                                "text":"add me",
                                "style":"danger",
                                "type":"button",
                                "value":"add me"
                            }
                        ]
                    }]

                resp = self.slack_client.api_call("chat.update",
                                                  channel=channel,
                                                  text=response,
                                                  ts=self.ts,
                                                  attachments=attachments,
                                                  as_user=True)
                return
            else:
                response = "There's already a game created, click `add me` if you want in."

        if command.lower().startswith("restart"):
            response = "Application restarted."
            resp = self.slack_client.api_call("chat.postMessage",
                                            channel=channel,
                                            text=response,
                                            as_user=True,
                                            attachments=attachments)
            restart_ts = resp['ts']
            event = "restart"
            models.log_message_ts(restart_ts,channel,event,team_id)
            return self.restart_program()

        if command.lower().startswith("remove me") and (self.game_started == False) and (self.game_created == True):
            if user_id not in self.users_in_game:
                response = "You haven't been added, so how can I remove you? Click `add me` if you want in."
            else:
                response = "Okay, {} removed from the game queue. When you have two or more players, click `start game`.".format(username)
                self.users_in_game.remove(user_id)

        if command.lower().startswith("add me"):
            if len(self.users_in_game) == 0:
                response = "There is no active game."
            else:
                if user_id in self.users_in_game:
                    response = "You've already been added to the game."
                else:
                    self.users_in_game.append(user_id)
                    response = "Added <@{}> to the game!".format(username)
                    response += "\n_`We have enough players to start a game.`_"
                    attachments = None
                    if len(self.users_in_game) >= 2:
                        attachments = [
                        {
                            "title":"Click start game once everyone is in",
                            "fallback":"Start the game or continue adding players.",
                            "callback_id":"start_add",
                            "color": "#3AA3E3",
                            "attachment_type":"default",
                            "actions": [
                                {
                                    "name":"add me",
                                    "text":"add me",
                                    "style":"danger",
                                    "type":"button",
                                    "value":"add me"
                                },
                                {
                                    "name":"start game",
                                    "text":"start game",
                                    "style":"primary",
                                    "type":"button",
                                    "value":"start game",
                                    "confirm":
                                    {
                                        "title": "Are you sure?",
                                        "text": "Has everyone added themselves to the game already?",
                                        "ok_text": "Yes",
                                        "dismiss_text": "No"
                                    }
                                },
                                {
                                    "name":"Lie. Cheat. Win!",
                                    "text":"mystery",
                                    "type":"button",
                                    "value":"gif",
                                    "confirm":
                                        {
                                            "title": "Do you dare?",
                                            "text": "There's no going back if you do this.",
                                            "ok_text": "I dare",
                                            "dismiss_text": "Nope"
                                        }
                                }
                            ]
                        }]

                    self.slack_client.api_call("chat.update",
                                                channel=channel,
                                                text=response,
                                                ts=self.ts,
                                                attachments=attachments,
                                                as_user=True)
                    return

        if command.lower().startswith("start game"):
            print "  Users in game: ", self.users_in_game
            if len(self.users_in_game) == 0:
                response = "No game exists yet."
            elif len(self.users_in_game) < 2:
                response = "There aren't enough players yet (minimum 2). Users can click `add me` to be added to the game."
            elif len(self.users_in_game) > 6:
                response = "There are too many players (max 6). Please try again."
            else:
                self.game_started = True
                response = ">>>Starting a new game of Drumpf!\n"
                self.score.initialize_scores()
                self.slack_client.api_call("chat.update",
                                          channel=channel,
                                          text=response,
                                          ts=self.ts,
                                          as_user=True)
                # self.ts = resp['ts']
                self.play_game_of_drumpf_on_slack(self.users_in_game, channel)
                return

        if command.lower().startswith("commands") or command.lower().startswith("help"):
            response = \
            ">>>Certainly, my liege. The available commands are: \n\n" \
            "*[bigly]*\tIt's a word.\n" \
            "*[cancel]*\tStop the current game.\n" \
            "*[commands]*\tView available commands.\n" \
            "*[comp]*\tView the card deck composition.\n" \
            "*[remove me]*\tRemove yourself from the current game queue.\n" \
            "*[rules/help]*\tView the rules of the game.\n" \
            "*[< _these_ > cards]*\tReplace < _these_ > with the cards you wish to view. i.e. 'Drumpf' cards.\n"

        if command.lower().startswith("rules") or command.lower().startswith("help"):
            response = ">>>Welcome to Drumpf! Check out the rules if you need some help: \n\n"
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

        if response:
            resp = self.slack_client.api_call("chat.postMessage",
                                            channel=channel,
                                            text=response,
                                            as_user=True, attachments=attachments)

    def handle_private_message(self,command,user_id,ts):
        """
        Controls how a private message incoming from a user is handled

        Args:
                [command] (str) incoming command to handle
                [user_id] (str) the id of the player
        """
        print "handle_private_message(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id

        response = ""

        if len(self.player_trump_card_queue):
            print "  len(self.player_trump_card_queue)"
            self.trump.handle_trump_suit_selection(command, user_id)

        elif len(self.player_bid_queue):
            print "  len(self.player_bid_queue)"
            self.bid.handle_player_bid(command, user_id)

        elif len(self.player_turn_queue):
            print "  len(self.player_turn_queue)"
            self.round_.handle_player_turn(command, user_id)

    def private_message_user(self, user_id, message, attachments=None):
        """
        Posts a private message to a user channel

        Args:
                [user_id] (str) id of the player
                [message] (str) the message to post
                [attachments] (list) a list of attachments to append to the message -optional, defaults to None
        """
        self.slack_client.api_call(
            "chat.postMessage",
            channel=user_id,
            text=message,
            as_user=True, attachments=attachments
        )

    def display_cards_for_player_in_pm(self, player_id, cards, msg):
        """
        Displays the cards for the players in a private message

        Args:
                [player_id] (str) id of the player
                [cards] (str) the cards to display
        """
        print "display_cards_for_player_in_pm(self, player_id, cards) "
        print "  player_id: ", player_id
        print "  player: ", self.user_ids_to_username[player_id]
        print "  cards: ", cards

        bot_im_id = models.get_bot_im_id(player_id,self.team_id)
        event = "init_cards_pm_" + str(self.current_game.current_round)
        ts = models.get_ts(bot_im_id,event,self.team_id)


        formatted_cards = helper_functions.interactiformat(cards)
        # the player has more than 5 cards, so we have to send them in separate messages
        self.first_set = False
        if len(cards) > 5:
            print "  len(cards) > 5"
            five_card_set = {}
            for idx, card in enumerate(cards):
                if idx == 0: # add the first card
                    self.first_set = True
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) != 0: # add the next 4
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) == 0: # we've hit the 5th card that sends a new message
                    attachments = helper_functions.interactify(five_card_set,self.first_set,msg)
                    self.slack_client.api_call("chat.update",
                                                channel=bot_im_id,
                                                as_user=True,
                                                ts=ts,
                                                attachments=attachments)
                    self.first_set = False
                    five_card_set.clear() # clear the set
                    five_card_set[idx] = formatted_cards[idx] # add the first card of the next set
                if len(cards) == (idx + 1): # we've reached the last card so post the remaining cards to the user
                    attachments = helper_functions.interactify(five_card_set,self.first_set,msg)
                    self.slack_client.api_call("chat.update",
                                                channel=bot_im_id,
                                                as_user=True,
                                                ts=ts,
                                                attachments=attachments)
                    five_card_set.clear()
        # there are less than 5 cards in the players hand, so just display them
        else:
            self.first_set = True
            attachments = helper_functions.interactify(formatted_cards,self.first_set,msg)
            self.slack_client.api_call("chat.update",
                                        channel=bot_im_id,
                                        as_user=True,
                                        ts=ts,
                                        attachments=attachments)

    def init_cards_for_player_in_pm(self, player_id, cards):
        """
        Initializes the cards for the players in a private message

        Args:
                [player_id] (str) id of the player
                [cards] (str) the cards to display
        """
        print "init_cards_for_player_in_pm(self, player_id, cards) "
        print "  player_id: ", player_id
        print "  player: ", self.user_ids_to_username[player_id]
        print "  cards: ", cards

        formatted_cards = helper_functions.interactiformat(cards)
        # the player has more than 5 cards, so we have to send them in separate messages
        self.first_set = True
        attachments = helper_functions.interactify(formatted_cards,self.first_set)
        resp = self.slack_client.api_call("chat.postMessage",channel=player_id,as_user=True,attachments=attachments)
        pm_ts = resp['ts']
        event = "init_cards_pm_" + str(self.current_game.current_round)
        bot_im_id = models.get_bot_im_id(player_id,self.team_id)
        models.log_message_ts(pm_ts,bot_im_id,event,self.team_id)

    def play_game_of_drumpf_on_slack(self, players, channel):
        """
        Takes an array of player_ids and the channel the game request originated from

        Args:
                [players] (list(Player())) a list of the player objects in game
                [channel] (str) the channel
        """
        print "play_game_of_drumpf_on_slack(self, players, channel) "
        print "  players: ", players
        print "  channel: ", channel

        player_objects = []
        for player_id in players:
            player_objects.append(DrumpfGame.Player(player_id))
        game = DrumpfGame.Game(player_objects, self, self.bid, self.trump)
        game.play_round()

    def prepare_for_next_round(self):
        """
        Clears all round and sub-round variables
        """
        print "prepare_for_next_round(self) "
        self.current_game.current_round += 1
        self.scoreboard = ""
        self.scores = ""
        for k in self.player_bids_for_current_round.keys():
            self.player_bids_for_current_round[k] = ""
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None
        self.sub_rounds_played = 0
        self.winning_sub_round_card = None
        self.winner_for_sub_round = None
        self.cards_played_for_sub_round = []
        self.zero_point_players = []
        self.shower_card_holder = []
        self.drumpfmendous_card_first = None
        self.player_bid_queue.clear()
        self.current_game.current_round_trump_suit = None
        self.first_card_sub_round = 0
        self.player_turn_queue.rotate(1)

    def make_channel(self):
        """
            Creates a new channel for Drumpfbot to reside
        """
        print "make_channel(self)"
        resp = self.slack.channels.create(
            name="drumpf-scoreboard"
            )
        print "  resp['channel']['id']:",resp['channel']['id']
        self.main_channel_id = resp['channel']['id']

    def list_users(self):
        """
            Gets a list of users in the timestamp

            Returns:
                    [users] (list) A list of user id's in the Slack team
        """
        print "list_users(self)"
        resp = self.slack.users.list()
        members = resp['members']
        users = []
        for member in members:
            users.append(member['id'])
        print "  users:",users
        return users

    def join_channel(self):
        """
            Adds the users in the Slack team to the main Drumpf channel
        """
        print "join_channel(self)"
        resp = self.slack.channels.join(
            name=self.main_channel_id
            )

    def restart_program(self):
        """
            Restarts the current program.
        """
        print "restart_program(self)"
        self.clear_ts_messages()
        models.clear_ts_messages(self.team_id)
        python = sys.executable
        os.kill(os.getpid(), 9)
        # os.execl(python, python, * sys.argv)

    def clear_ts_messages(self):
        team_id = self.team_id
        connection = models.connect()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT channel, ts FROM `messages` WHERE team_id=%s"
                data = (team_id)
                cursor.execute(sql,data)
                results = cursor.fetchall()
                for result in results:
                    print "  result['channel']:",result['channel']
                    print "  result['ts']:",result['ts']
                    try:
                        resp = self.slack_client.api_call("chat.delete", channel=result['channel'],ts=result['ts'],as_user=True)
                    except:
                        print "  failed on slack_client delete call..."
                    else:
                        print "  successful deletion of message in channel"
        except Exception as e:
            raise
        else:
            print "  Successfully updated user name in users table."
        finally:
            connection.close()

    def parse_slack_output(self):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = self.slack_client.rtm_read()
        if output_list and len(output_list) > 0:
            # print output_list
            for output in output_list:
                if output and 'text' in output and self.AT_BOT in output['text']:
                    # return text after the @ mention, whitespace removed
                    if 'ts' in output:
                        return output['text'].split(self.AT_BOT)[1].strip().lower(), output['channel'], output['user'], output['ts']
                    else:
                        print "SELF.AT_BOT2: ",self.AT_BOT
                        return output['text'].split(self.AT_BOT)[1].strip().lower(), output['channel'], output['user'], None
        return None, None, None, None

    def initialize(self, user_id, channel_id):
        """
        Initializes the bot with the necessary global variables

        Args:
                [user_id] (str) id of the player
                [channel_id] (str) the main channel for the team the app is initialized from
        """
        print "initialize(self, user_id, channel)"
        print "  user_id",user_id
        print "  channel",channel_id

        token = models.get_bot_access_token(user_id)
        try:
            self.BOT_TOKEN = token
            self.slack_client = SlackClient(token)
            self.slack = Slacker(token)
            test_call = self.slack_client.api_call("users.list")

            if test_call.get('ok'):
                print "  test call is OKIE DOKIE"
                self.BOT_ID = models.get_bot_user_id(token)
                self.AT_BOT = "<@" + self.BOT_ID + ">"
                members = self.slack_client.api_call('users.list').get('members')
                for member in members:
                    self.user_ids_to_username[member['id']] = member['name']
                    connection = models.connect()
                    try:
                        with connection.cursor() as cursor:
                            sql = "UPDATE `users` SET name=%s WHERE user_id=%s"
                            data = (member['name'],member['id'])
                            cursor.execute(sql,data)
                    except Exception as e:
                        raise
                    else:
                        print "  Successfully updated user name in users table."
                    finally:
                        connection.close()
                channels = self.slack_client.api_call("channels.list").get('channels')
                for channel in channels:
                    self.channel_ids_to_name[channel['id']] = channel['name']

                if "drumpf-scoreboard" not in [channel['name'] for channel in channels]:
                    self.make_channel()
                    users = self.list_users()
                    for user in users:
                        self.join_channel()
                else:
                    print "  Existing #drumpf-scoreboard channel found..."
                    self.main_channel_id = channel_id
                    print "  self.main_channel_id: ",self.main_channel_id
        except Exception as e:
            print "  Exception raised!"
            raise
        else:
            print "  Successful token retrieval"

    def main(self, score, bid, trump, round_, team_id):
        """
            Opens a Slack RTM API websocket connection

            Args:
                    [score/bid/trump/round_] (Obj) The instantiated objects needed to play the game
                    [team_id] (str) The team id of the relevant Slack team
        """
        self.score = score
        self.bid = bid
        self.trump = trump
        self.round_ = round_
        self.team_id = team_id

        READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
        #grab user list and converts it to to a dict of ids to usernames

        if self.slack_client.rtm_connect():
            print("DRUMPFBOT v0.9 connected and running!")
            message = ""
            attachments = [
                {
                    "title":"Select a game style:",
                    "fallback":"Select a game style:",
                    "callback_id":"game style",
                    "color": "#3AA3E3",
                    "attachment_type":"default",
                    "actions": [
                        {
                            "name":"create game",
                            "text":"Standard",
                            "type":"button",
                            "value":"create game",
                            "confirm":
                            {
                                "title": "Are you sure?",
                                "text": "This can take a while. The game will go until there are no cards left to deal (from the 60 card deck). That means 30 rounds for two people, 20 rounds for three, and so on.",
                                "ok_text": "Yes",
                                "dismiss_text": "No"
                            }
                        },
                        {
                            "name":"create game 250",
                            "text":"First to 250 pts",
                            "type":"button",
                            "value":"create game 250"
                        },
                        {
                            "name":"create game 500",
                            "text":"First to 500 pts",
                            "type":"button",
                            "value":"create game 500"
                        },
                        {
                            "name":"create game 1000",
                            "text":"First to 1000 pts",
                            "type":"button",
                            "value":"create game 1000"
                        }
                    ]
                }]

            # sql = "SELECT ts FROM `messages` WHERE event='wake_bot' AND team_id='{}'".format(self.team_id)
            # engine = models.get_engine()
            # df = pd.read_sql_query(sql=sql,con=engine)
            self.ts = models.get_ts(self.main_channel_id,"wake_bot",self.team_id)

            self.slack_client.api_call("chat.update",
                                        channel=self.main_channel_id,
                                        text=message,
                                        ts = self.ts,
                                        attachments=attachments,
                                        as_user=True)
            while True:
                command, channel, user, ts = self.parse_slack_output()
                if command and channel:
                    if channel not in self.channel_ids_to_name.keys():
                        #this (most likely) means that this channel is a PM with the bot
                        self.handle_private_message(command, user, ts)
                    else:
                        self.handle_command(command, channel, user, ts)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
