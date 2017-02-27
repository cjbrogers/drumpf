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
from scoring import Scoring
from bidding import Bid

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(helper_functions.get_slack_client())
slack = Slacker(helper_functions.get_slack_client())
SUITS = ["diamonds", "clubs", "hearts", "spades"]

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
        #self.player_bids_for_current_round = [] #[1, 1, 0]
        self.player_bids_for_current_round = {} #{"U3LCLSTA5": 1, "U3MP47XAB": 0}
        self.current_game = None #DrumpfGame.Game() object
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None #string

        #SUB-ROUND VARIABLES
        self.cards_played_for_sub_round = [] #this mirrors player_turn_queue as to determine a winner
        self.winner_for_sub_round = None
        self.sub_rounds_played = 0
        self.winning_sub_round_card = None
        self.zero_point_players = [] #if users play blacks card in a sub round they get 0 points for that round
        self.shower_card_holder = [] # holds the player who holds the golden shower card

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
                response = ">>>Starting a new game of Drumpf with players: \n" + self.get_readable_list_of_players()

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

    def handle_trump_suit_selection(self,command,user_id):
        print "handle_trump_suit_selection(command, user_id) "
        print "  command: ",command
        print "  user_id: ",user_id
        print "  player: ", self.user_ids_to_username[user_id]

        response = ""
        current_username = self.user_ids_to_username[self.player_trump_card_queue[0]]
        #we're waiting for a user to select a trump card
        print "  self.player_trump_card_queue[0]: {}".format(self.player_trump_card_queue[0])
        if user_id != self.player_trump_card_queue[0]:
            print "  Waiting for <@{}> to select a trump suit".format(current_username)
            response = "Waiting for <@{}> to select a trump suit".format(current_username)
        elif user_id == self.player_trump_card_queue[0]:
            print "  user_id == self.player_trump_card_queue[0]"
            #validate that the dealer picked a valid trump suit
            if (0 <= int(command) <= 3):
                print "  0 <= int(command) <= 3"

                print "  self.current_game.current_round_trump_suit WAS: {}".format(self.current_game.current_round_trump_suit)
                self.current_game.current_round_trump_suit = SUITS[int(command)]
                print "  self.current_game.current_round_trump_suit SET TO: {}".format(self.current_game.current_round_trump_suit)

                # print "  Trump suit recorded! Check the main channel."
                # response = "Trump suit recorded! Check the main channel."

                msg = "<@{}> chose :{}: for the trump suit.\n".format(current_username, SUITS[int(command)])
                print " ",msg
                score.build_scoreboard(msg)
                score.update_scoreboard(self.scoreboard)

                print "    self.player_trump_card_queue before pop(): {}".format(self.player_trump_card_queue)

                self.player_trump_card_queue.pop()

                print "    self.player_trump_card_queue after pop(): {}".format(self.player_trump_card_queue)

                for player in self.player_turn_queue_reference:
                    self.private_message_user(player, response)
                    self.private_message_user(player, msg)

                if len(self.player_bid_queue):
                    bid.present_bid_buttons(self.player_bid_queue[0])
                    msg = "What's your bid for the round?"
                    print "  ",msg
                else:
                    msg = "Play a card."
                    print "  ",msg
                    for player in self.current_game.players:
                        if player.id == self.player_turn_queue[0]:
                            self.display_cards_for_player_in_pm(self.player_turn_queue[0],player.cards_in_hand)
                            self.private_message_user(self.player_turn_queue[0], "Play a card.")
                return
            else:
                print "  That wasn't a valid index for a trump suit."
                response = "That wasn't a valid index for a trump suit."
        else:
            print "Whoops! Something went wrong."

        self.private_message_user(user_id, response)

    def get_card_being_played(self, user_id, index): # -> ex. ['K', 'spades']
        print "get_card_being_played(self, user_id, index) "
        print "  user_id: ",user_id
        print "  player: ", self.user_ids_to_username[user_id]
        print "  index: ",index

        for user_object in self.current_game.players:
            if user_object.id == user_id:
                print "  cards in hand: {}".format(user_object.cards_in_hand)
                if index > len(user_object.cards_in_hand):
                    return None
                else:
                    return user_object.cards_in_hand[index]

    def handle_player_turn(self, command, user_id):
        print "handle_player_turn(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id
        print "  player: ", self.user_ids_to_username[user_id]

        response = ""
        current_username = self.user_ids_to_username[self.player_turn_queue[0]]
        print("  User sending message: {}".format(self.user_ids_to_username[user_id]))
        #waiting for first player after dealer to play a card
        if user_id != self.player_turn_queue[0]:
            response = "Waiting for <@{}> to play a card.".format(current_username)
        elif user_id == self.player_turn_queue[0]:
            print('  Received input from expected player: {}'.format(current_username))

            print "  self.current_game.current_round: {}".format(self.current_game.current_round)

            print "  self.sub_rounds_played + 1 : {}".format(self.sub_rounds_played + 1)

            allowable_index = int(self.current_game.current_round) - (int(self.sub_rounds_played) + 1)
            print "  set allowable_index: {}".format(allowable_index)

            # the command must be between 0 and the largest index of the card in the players hand
            if int(command) >= 0 and int(command) <=  allowable_index:
                print("  Selected a valid card index")
                card_being_played = self.get_card_being_played(user_id, int(command))

                if card_being_played == None:
                    self.private_message_user(user_id, "That's not a valid card index")
                    return
                card_value = None
                card_suit = None

                if len(card_being_played) == 2: # regular card
                    card_value = str(card_being_played[0])
                    print "  Card Value: ", card_value
                    card_suit = card_being_played[1]
                    print "  Card Suit: ", card_suit
                else: # special card
                    card_value = card_being_played
                    print "  Card Value: ", card_value
                    card_suit = None

                self.first_card_sub_round += 1


                #otherwise valid card played
                if self.leading_suit != None:
                    print "  self.leading_suit != None"
                    print("  Sub-round trump suit: {}".format(self.leading_suit))
                    #a drumpf or a visible minority card or a tremendous card is always a valid play
                    if card_value.startswith("d_") or card_value.startswith("vm_") or card_value.startswith("t_"):
                        self.handle_valid_card_played(card_being_played)
                    elif self.leading_suit == "Any":
                        #a drumpf was played as the first card
                        #players are free to play whatever they want
                        self.handle_valid_card_played(card_being_played)
                    elif card_suit == self.leading_suit:
                        #card played same suit as sub_round_suit
                        self.handle_valid_card_played(card_being_played)
                    elif self.player_hand_contains_suit(user_id, self.leading_suit) == False:
                        #any card is valid, because player doesn't have the initial suit
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.private_message_user(user_id, "Sorry, you can't play that card")
                elif self.leading_suit == None:
                    print("  There is no sub-round trump suit set yet....")
                    if card_value.startswith("d_") or card_value.startswith("t_"):
                        print("  {} played a Drumpf or Tremendous  Card first".format(current_username))
                        # nasty card played first gets to set suit
                        if self.first_card_sub_round == 1:
                            print "  self.first_card_sub_round == 1"
                            if "t_nasty" in card_value:
                                print "  player holds t_nasty and so gets to choose trump suit"
                                self.prompt_dealer_for_trump_suit(user_id)
                            else:
                                self.leading_suit = "Any"
                                self.handle_valid_card_played(card_being_played)
                        else:
                            self.leading_suit = "Any"
                            self.handle_valid_card_played(card_being_played)
                    elif card_value.startswith("vm_"):
                        print("  {} played a Visible Minority Card".format(current_username))
                        #the sub round suit stays None until a player plays a suited card
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.leading_suit = card_suit
                        print("  Sub-round trump suit set to {}".format(card_suit))
                        self.handle_valid_card_played(card_being_played)
            else:
                response = "That wasn't a valid card index."
        self.private_message_user(user_id, response)

    def player_hand_contains_suit(self, user_id, suit):
        print "player_hand_contains_suit(self, user_id, suit) "
        print "  Checking if player hand contains expected suit:  {}".format(self.leading_suit)
        for user_object in self.current_game.players:
            if user_object.id == user_id:
                card_value = None
                card_suit = None
                for card_obj in user_object.cards_in_hand:
                    if len(card_obj) == 2:
                        card_value = str(card_obj[0])
                        card_suit = card_obj[1]
                    else:
                        card_value = str(card_obj)
                        card_suit = None
                    if "d_" not in card_value and "t_" not in card_value and "vm_" not in card_value:
                        if card_suit == suit:
                            return True
        return False

    def handle_valid_card_played(self, card):
        print "handle_valid_card_played(self, card) "
        print "  card: ",card

        player_who_played_card = self.user_ids_to_username[self.player_turn_queue[0]]
        self.remove_card_from_players_hand(self.player_turn_queue[0], card)

        card_emoji = helper_functions.emojify_card(card)
        msg = "><@{}> played {}\n".format(player_who_played_card, card_emoji)
        print " ",msg
        score.build_scoreboard(msg)
        score.update_scoreboard(self.scoreboard)
        # self.message_main_game_channel(msg)

        self.cards_played_for_sub_round.append(card)
        print("  Cards played for sub-round: {}".format(self.cards_played_for_sub_round))

        print "    self.player_turn_queue before popleft(): {}".format(self.player_turn_queue)
        self.player_turn_queue.popleft()
        print "    self.player_turn_queue after popleft(): {}".format(self.player_turn_queue)

        print("  Player turn queue: {}".format(self.player_turn_queue))
        if len(self.player_turn_queue) == 0:
            self.sub_rounds_played += 1

            print("  >Everyone played, time to determine winner for sub-round")
            score.determine_winner_for_sub_round(card)

            self.player_points_for_round[self.winner_for_sub_round] += 1

            msg = ">*<@{}> won this sub-round with a {}*\n\n".format(self.winner_for_sub_round,helper_functions.emojify_card(self.winning_sub_round_card))
            print " ",msg
            score.build_scoreboard(msg)
            score.update_scoreboard(self.scoreboard)
            # self.message_main_game_channel(msg, attachments=self.attachments)

            #reset all sub-round variables
            self.leading_suit = None
            self.cards_played_for_sub_round = []

            if self.sub_rounds_played == self.current_game.current_round:
                print "  >Sub-round is over, time to tally points and display them"
                print "    player_turn_queue: %s" % self.player_turn_queue
                print "    player_bid_queue: %s" % self.player_bid_queue
                print "    self.users_in_game: %s" % self.users_in_game
                print "    self.player_bids_for_current_round: %s" % self.player_bids_for_current_round

                score.calculate_and_display_points_for_players()
                self.winner_for_sub_round = None
            elif self.sub_rounds_played < self.current_game.current_round:
                msg = ">_Sub-Round {}_\n".format(self.sub_rounds_played + 1)
                score.build_scoreboard(msg)
                score.update_scoreboard(self.scoreboard)
                # self.message_main_game_channel(msg)

                #initialize another turn queue cause there are more cards to play
                self.player_turn_queue = copy.copy(self.users_in_game)

                print "    player_turn_queue: %s" % self.player_turn_queue
                print "    player_bid_queue: %s" % self.player_bid_queue
                print "    self.users_in_game: %s" % self.users_in_game
                print "    self.player_bids_for_current_round: %s" % self.player_bids_for_current_round

                while self.player_turn_queue[0] != self.winner_for_sub_round:
                    print("  *Rotating player turn queue")
                    #rotate player_turn_queue until the first player is the one who won
                    self.player_turn_queue.rotate(1)
                    # self.player_bid_queue.rotate(1)
                    # self.users_in_game.rotate(1)

                print "    player_turn_queue: %s" % self.player_turn_queue
                print "    player_bid_queue: %s" % self.player_bid_queue
                print "    self.users_in_game: %s" % self.users_in_game
                print "    self.player_bids_for_current_round: %s" % self.player_bids_for_current_round

                self.player_turn_queue_reference = copy.copy(self.player_turn_queue)
                self.winner_for_sub_round = None
                for player in self.current_game.players:
                    if player.id == self.player_turn_queue[0]:
                        self.display_cards_for_player_in_pm(self.player_turn_queue[0],player.cards_in_hand)
                        self.private_message_user(self.player_turn_queue[0], "Play a card.")
        else:
            for player in self.current_game.players:
                if player.id == self.player_turn_queue[0]:
                    self.display_cards_for_player_in_pm(self.player_turn_queue[0],player.cards_in_hand)
                    self.private_message_user(self.player_turn_queue[0], "Play a card.")

    # clears all round and sub-round variables
    def prepare_for_next_round(self):
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
        # self.player_bid_queue.rotate(1)

    def remove_card_from_players_hand(self, current_player_id, card_to_remove):
        print "remove_card_from_players_hand(self, current_player_id, card_to_remove) "
        print "  current_player_id: ",current_player_id
        print "  player: ", self.user_ids_to_username[current_player_id]
        print "  card_to_remove: ",card_to_remove

        idx_of_card_to_remove = None
        for player in self.current_game.players:
            if player.id == current_player_id:
                #we found the player, now remove the appropriate card from his/her hand
                for idx, card in enumerate(player.cards_in_hand):
                    if card == card_to_remove:
                        idx_of_card_to_remove = idx
                player.cards_in_hand.pop(idx_of_card_to_remove)

    def message_main_game_channel(self, message, attachments=None):
        slack_client.api_call(
            "chat.postMessage",
            channel=self.main_channel_id,
            text=message,
            as_user=True, attachments=attachments
        )

    def private_message_user(self, user_id, message, attachments=None):
        slack_client.api_call(
            "chat.postMessage",
            channel=user_id,
            text=message,
            as_user=True, attachments=attachments
        )

    def handle_private_message(self,command,user_id):
        print "handle_private_message(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id

        response = ""

        print "  **$$**len(self.player_trump_card_queue): {}".format(len(self.player_trump_card_queue))
        print "  **$$**self.player_trump_card_queue: {}".format(self.player_trump_card_queue)

        print "  **$$**len(self.player_bid_queue): {}".format(len(self.player_bid_queue))
        print "  **$$**self.player_bid_queue: {}".format(self.player_bid_queue)

        print "  **$$**len(self.player_turn_queue): {}".format(len(self.player_turn_queue))
        print "  **$$**self.player_turn_queue: {}".format(self.player_turn_queue)

        if len(self.player_trump_card_queue):
            print "  len(self.player_trump_card_queue)"
            self.handle_trump_suit_selection(command, user_id)

        elif len(self.player_bid_queue):
            print "  len(self.player_bid_queue)"
            bid.handle_player_bid(command, user_id)

        elif len(self.player_turn_queue):
            print "  len(self.player_turn_queue)"
            self.handle_player_turn(command, user_id)

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

    def prompt_dealer_for_trump_suit(self, player_id):
        print "prompt_dealer_for_trump_suit(self, player_id) "
        print "  player_id: ", player_id
        print "  player: ", self.user_ids_to_username[player_id]
        self.dealer_prompted_for_trump_suit = True

        print "  self.player_trump_card_queue before append(): {}".format(self.player_trump_card_queue)
        self.player_trump_card_queue.append(player_id)
        print "  self.player_trump_card_queue after append(): {}".format(self.player_trump_card_queue)

        attachments =[{"title":"Please select index for trump suit:", "fallback":"Your interface does not support interactive messages.", "callback_id":"prompt_trump_suit", "attachment_type":"default", "actions":[{"name":"diamonds","text":":diamonds:","type":"button","value":"0"},
        {"name":"clubs","text":":clubs:","type":"button","value":"1"},
        {"name":"hearts","text":":hearts:","type":"button","value":"2"},
        {"name":"spades","text":":spades:","type":"button","value":"3"}]}]
        slack.chat.post_message(
            channel=player_id,
            as_user=True,
            attachments=attachments
            )

    def get_readable_list_of_players(self):
        print "get_readable_list_of_players(self) "
        player_names = []
        printable_player_names = []
        for player_id in self.users_in_game:
            player_names.append(self.user_ids_to_username[player_id])
        for idx, player_name in enumerate(player_names):
            printable_player_names.append("{}) <@{}>".format(idx + 1, player_name))
        return (' \n ').join(printable_player_names)

    def display_cards_for_player_in_pm(self, player_id, cards):
        print "display_cards_for_player_in_pm(self, player_id, cards) "
        print "  player_id: ", player_id
        print "  player: ", self.user_ids_to_username[player_id]
        print "  cards: ", cards

        formatted_cards = helper_functions.interactiformat(cards)
        # the player has more than 5 cards, so we have to send them in separate messages
        self.first_set = False
        if len(cards) > 5:
            print "  len(cards) > 5"
            five_card_set = {}
            for idx, card in enumerate(cards):
                if idx == 0: # add the first card
                    self.first_set = True
                    print "  idx == 0"
                    print "  formatted_cards[idx] = ", formatted_cards[idx]
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) != 0: # add the next 4
                    print "  (idx % 5) != 0"
                    print "  formatted_cards[idx] = ", formatted_cards[idx]
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) == 0: # we've hit the 5th card that sends a new message
                    print "  (idx % 5) == 0"
                    attachments = helper_functions.interactify(five_card_set,self.first_set)
                    print "  *posting whole set of five"
                    slack.chat.post_message(
                        channel=player_id,
                        as_user=True,
                        attachments=attachments
                        )
                    self.first_set = False
                    five_card_set.clear() # clear the set
                    five_card_set[idx] = formatted_cards[idx] # add the first card of the next set
                    print "  five_card_set (first card of next set): ", five_card_set
                if len(cards) == (idx + 1): # we've reached the last card so post the remaining cards to the user
                    print "  len(cards) == (idx + 1)"
                    attachments = helper_functions.interactify(five_card_set,self.first_set)
                    print "  *posting remaining set of cards"
                    slack.chat.post_message(
                        channel=player_id,
                        as_user=True,
                        attachments=attachments
                        )
                    five_card_set.clear()
        # there are less than 5 cards in the players hand, so just display them
        else:
            print "  len(cards) <= 5"
            self.first_set = True
            attachments = helper_functions.interactify(formatted_cards,self.first_set)
            print "  *posting set of 0-5"
            slack.chat.post_message(
                channel=player_id,
                as_user=True,
                attachments=attachments
                )

    def announce_trump_card(self, trump_card):
        print "announce_trump_card(self, trump_card) "
        print "  trump_card: ",trump_card

        msg = "*Round {}* \n The trump card is: {} \n>_Sub-Round {}_\n".format(
            self.current_game.current_round,
            helper_functions.emojify_card(trump_card),(self.sub_rounds_played + 1))
        score.build_scoreboard(msg)
        score.update_scoreboard(self.scoreboard)
        trump = "The trump card is: {} \n".format(helper_functions.emojify_card(trump_card))
        # send the trump suit to pm
        for player_id in self.users_in_game:
            self.private_message_user(player_id,trump)

    #takes an array of player_ids and the channel the game request originated from
    def play_game_of_drumpf_on_slack(self, players, channel):
        print "play_game_of_drumpf_on_slack(self, players, channel) "
        print "  players: ", players
        print "  channel: ", channel

        player_objects = []
        for player_id in players:
            player_objects.append(DrumpfGame.Player(player_id))
        game = DrumpfGame.Game(player_objects, self, bid)
        game.play_round()

    #Restarts the current program.
    def restart_program(self):
        print "restart_program(self)"
        python = sys.executable
        os.execl(python, python, * sys.argv)

    def main(self):
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
    bid = Bid(bot)
    score = Scoring(bot)
    bot.main()
