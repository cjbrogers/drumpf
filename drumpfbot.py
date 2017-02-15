# -*- coding: utf-8 -*-
import os
import sys
import time
import copy

from slackclient import SlackClient
from collections import defaultdict
from collections import deque

import drumpfgame as DrumpfGame
import helper_functions

if not os.environ.get("BOT_ID") or not os.environ.get("SLACK_BOT_TOKEN"):
    os.environ["BOT_ID"] = "U41R44L82"
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-137854156274-"\
        "ZKlVGuPYXT8zgRmahoIzgeio"

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

suits = ["diamonds", "clubs", "hearts", "spades"]

class DrumpfBot:
    def __init__(self, main_channel_id='C41Q1H4BD'):
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
        self.player_bids_for_current_round = [] #[1, 1, 0]
        self.current_game = None #DrumpfGame.Game() object
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None #string

        #SUB-ROUND VARIABLES
        self.cards_played_for_sub_round = [] #this mirrors player_turn_queue as to determine a winner
        self.winner_for_sub_round = None
        self.sub_rounds_played = 0
        self.winning_sub_round_card = None
        self.zero_point_players = [] #if users play blacks card in a sub round they get 0 points for that round

        self.attachments = None
        self.game_started = False
        self.game_created = False
        self.debug = False

    def handle_command(self, command, channel, user_id):
        print "handle_command(self, command, channel, user_id) "
        print "  command: ", command
        print "  channel: ", channel
        print "  user_id: ", user_id

        attachments = None
        #TODO restrict the channel this is in
        username = self.user_ids_to_username[user_id] #user who sent the message

        response = "Wrong! Bing-bing-bing! Try `@drumpfbot help` for a tremendous list of available commands."

        if command.lower().startswith("debug"):
            self.debug = True
            response = ">>>Now entering debug mode. \n"
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text=response, as_user=True)
            self.game_created == True
            self.users_in_game.append(user_id)
            self.users_in_game.append('U44V02PDY') #Roberto U3LCLSTA5 Alex U3LNCN0F3 Gordi-bot U42H6H9L5 Slackbot USLACKBOT drumpfbot U41R44L82 Cam U3N36HRHU James U3MP47XAB Test Icle U44V02PDY
            response = ""
            self.handle_command("start game", channel, user_id)
            # return

        if command.lower().startswith("create game"):
            self.game_created == True
            if len(self.users_in_game) == 0:
                response = "<@{}> Wants to play a game of drumpf! Type `@drumpfbot add me` to play.".format(username)
                self.users_in_game.append(user_id)
            else:
                response = "There's already a game being made, say `@drumpfbot add me` if you want in."

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

        if command.lower().startswith("start game"):
            print "Users in game: ", self.users_in_game
            if len(self.users_in_game) == 0:
                response = "No game exists yet. Try `@drumpfbot create game`"
            elif len(self.users_in_game) < 2:
                response = "There aren't enough players yet (minimum 3). Users can say `add me` to be added to the game."
            elif len(self.users_in_game) > 6:
                response = "There are too many players (max 6). Please try again."
            else:
                self.game_started = True
                response = ">>>Starting a new game of Drumpf with players: \n" + self.get_readable_list_of_players()
                if self.debug:
                    response += "\n`DEBUG MODE ACTIVE`"
                slack_client.api_call("chat.postMessage", channel=channel,
                                      text=response, as_user=True)
                self.play_game_of_drumpf_on_slack(self.users_in_game, channel)
                return #have to do this because we want the "new game" message to come before the trump card announcement

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
            response = ">>>Are WASP'S _really_ still a thing? \n"
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

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True, attachments=attachments)

    def handle_trump_suit_selection(self, command, user_id):
        print "handle_trump_suit_selection(command, user_id) "
        print "  command: ",command
        print "  user_id: ",user_id

        response = ""
        current_username = self.user_ids_to_username[self.player_trump_card_queue[0]]
        #we're waiting for a user to select a trump card
        if user_id != self.player_trump_card_queue[0]:
            response = "Waiting for <@{}> to select a trump suit".format(current_username)
        elif user_id == self.player_trump_card_queue[0]:
            #validate that the dealer picked a valid trump suit
            try:
                if 0 <= int(command) <= 3:
                    self.current_game.current_round_trump_suit = suits[int(command)]
                    response = "Trump suit recorded! Check the main channel."
                    slack_client.api_call(
                        "chat.postMessage",
                        channel=self.main_channel_id,
                        text="<@{}> chose :{}: for the trump suit.".format(current_username, suits[int(command)]),
                        as_user=True
                    )
                    self.private_message_user(self.player_bid_queue[0], "What's your bid for the round?")
                    self.player_trump_card_queue.pop()
                else:
                    response = "That wasn't a valid index for a trump suit."
            except:
                response = "That's not a valid command. Please select a trump suit."
        else:
            print "Whoops! Something went wrong."

        self.private_message_user(user_id, response)

    def get_card_being_played(self, user_id, index): # -> ex. ['K', 'spades']
        print "get_card_being_played(self, user_id, index) "
        print "  user_id: ",user_id
        print "  index: ",index

        for user_object in self.current_game.players:
            if user_object.id == user_id:
                print(user_object.cards_in_hand)
                if index > len(user_object.cards_in_hand):
                    return None
                else:
                    return user_object.cards_in_hand[index]

    def handle_player_bid(self, command, user_id):
        print "handle_player_bid(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id

        current_username = self.user_ids_to_username[self.player_bid_queue[0]]
        #we're waiting for the first player in queue to bid
        if user_id != self.player_bid_queue[0]:
            response = "We're still waiting on <@{}> to bid.".format(current_username)
        elif user_id == self.player_bid_queue[0]:
            #expected user to bid
            try:
                if 0 > int(command) > self.current_game.current_round:
                    response = "You can't bid that amount!"
                else:
                    #valid bid
                    self.player_bids_for_current_round.append(int(command))
                    response = "Bid recorded! Check the main channel."
                    slack_client.api_call(
                        "chat.postMessage",
                        channel=self.main_channel_id,
                        text="<@{}> bids `{}`.".format(current_username, int(command)),
                        as_user=True
                    )
                    self.player_bid_queue.popleft()
                    if len(self.player_bid_queue) == 0:
                        #everyone bidded, time to play sub_round
                        slack_client.api_call(
                            "chat.postMessage",
                            channel=self.main_channel_id,
                            text="All bids recorded, let's play!",
                            as_user=True
                        )
                        self.private_message_user(self.player_turn_queue[0], "Please select a card `index` to play.")
                    else: #get the next player's bid
                        self.private_message_user(self.player_bid_queue[0], "What's your bid for the round?")
            except:
                response = "That wasn't a valid bid."

        self.private_message_user(user_id, response)

    def handle_player_turn(self, command, user_id):
        print "handle_player_turn(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id

        response = ""
        current_username = self.user_ids_to_username[self.player_turn_queue[0]]
        print("  User sending message: {}".format(self.user_ids_to_username[user_id]))
        #waiting for first player after dealer to play a card
        if user_id != self.player_turn_queue[0]:
            response = "Waiting for <@{}> to play a card.".format(current_username)
        elif user_id == self.player_turn_queue[0]:
            print('  Received input from expected player: {}'.format(current_username))
            #validate the int(command) index selected is within the range of cards in hand
            if int(command) >= 0 and int(command) < self.current_game.current_round:

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
                #otherwise valid card played
                if self.leading_suit != None:
                    print("  Sub-round trump suit: {}".format(self.leading_suit))
                    #a drumpf or a visible minority card or a tremendous card is always a valid play
                    if card_value.startswith("D:") or card_value.startswith("VM:") or card_value.startswith("T:"):
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
                    if card_value.startswith("D:") or card_value.startswith("T:"):
                        print("{} played a Drumpf Card".format(current_username))
                        self.leading_suit = "Any"
                        self.handle_valid_card_played(card_being_played)
                    elif card_value.startswith("VM:"):
                        print("{} played a Visible Minority Card".format(current_username))
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
                    if "D:" not in card_value and "T:" not in card_value and "VM:" not in card_value:
                        if card_suit == suit:
                            return True
        return False

    def handle_valid_card_played(self, card):
        print "handle_valid_card_played(self, card) "
        print "  card: ",card

        player_who_played_card = self.user_ids_to_username[self.player_turn_queue[0]]
        self.remove_card_from_players_hand(self.player_turn_queue[0], card)
        card_emoji = helper_functions.emojify_card(card)

        self.message_main_game_channel("><@{}> played {}".format(player_who_played_card, card_emoji))
        self.cards_played_for_sub_round.append(card)
        print("  Cards played for sub-round: {}".format(self.cards_played_for_sub_round))
        self.player_turn_queue.popleft()
        print("  Player turn queue: {}".format(self.player_turn_queue))
        if len(self.player_turn_queue) == 0:
            self.sub_rounds_played += 1
            print("  >Everyone played, time to determine winner for sub-round")
            self.determine_winner_for_sub_round(card)
            self.player_points_for_round[self.winner_for_sub_round] += 1
            self.message_main_game_channel(">*<@{}> won this sub-round with a {}*".format(
                self.winner_for_sub_round, helper_functions.emojify_card(self.winning_sub_round_card)), attachments=self.attachments)
            #reset all sub-round variables
            self.leading_suit = None
            self.cards_played_for_sub_round = []

            if self.sub_rounds_played == self.current_game.current_round:
                print("  >Sub-rounds over, time to tally points and display them")
                self.calculate_and_display_points_for_players()
                self.winner_for_sub_round = None
            elif self.sub_rounds_played < self.current_game.current_round:
                self.message_main_game_channel(">_Sub-Round {}_".format(self.sub_rounds_played + 1))
                #initialize another turn queue cause there are more cards to play
                self.player_turn_queue = copy.copy(self.users_in_game)
                while self.player_turn_queue[0] != self.winner_for_sub_round:
                    print("  *Rotating player turn queue")
                    #rotate player_turn_queue until the first player is the one who won
                    self.player_turn_queue.rotate(1)
                self.player_turn_queue_reference = copy.copy(self.player_turn_queue)
                self.winner_for_sub_round = None
                self.private_message_user(self.player_turn_queue[0], "Play a card `index`")
        else:
            self.private_message_user(self.player_turn_queue[0], "Play a card `index`")

    def calculate_and_display_points_for_players(self):
        print "calculate_and_display_points_for_players(self) "
        self.message_main_game_channel("*Round {} over!* _calculating points..._".format(self.current_game.current_round))
        for idx, player_id in enumerate(self.users_in_game):
            current_players_bid = self.player_bids_for_current_round[idx]
            points_off_from_bid = abs(current_players_bid - self.player_points_for_round[player_id])
            slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                  text="current_players_bid: %s" % current_players_bid, as_user=True)
            slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                  text="points_off_from_bid: %s" % points_off_from_bid, as_user=True)
            if self.user_ids_to_username[player_id] == self.shower_card_holder:
                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id]: %s" % self.game_scorecard[player_id], as_user=True)
                self.game_scorecard[player_id] += 175
                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id] + 175: %s" % self.game_scorecard[player_id], as_user=True)
            elif self.user_ids_to_username[player_id] in self.zero_point_players:
                self.game_scorecard[player_id] += 0
            elif points_off_from_bid == 0:

                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id]: %s" % self.game_scorecard[player_id], as_user=True)
                #The player got his/her bid correctly
                self.game_scorecard[player_id] += (50 + 25 * current_players_bid)
                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id] + (50 + 25 * bid): %s" % self.game_scorecard[player_id], as_user=True)
            else:
                #player loses 25-points for every point above or below bid
                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id]: %s" % self.game_scorecard[player_id], as_user=True)
                self.game_scorecard[player_id] -= 25 * points_off_from_bid
                slack_client.api_call("chat.postMessage", channel=channel, #debbug delete after
                                      text="self.game_scorecard[player_id] -25 * points off bid: %s" % self.game_scorecard[player_id], as_user=True)
        self.message_main_game_channel(">*Score Board*")
        for player_id in self.users_in_game:
            self.message_main_game_channel("><@{}>: *{} Points*".format(self.user_ids_to_username[player_id], self.game_scorecard[player_id]))
        print(self.current_game)
        self.prepare_for_next_round()
        if self.current_game.current_round == self.current_game.final_round:
            self.present_winner_for_game()
        else:
            self.current_game.play_round()

    def present_winner_for_game(self):
        print "present_winner_for_game(self) "
        pass

    # clears all round and sub-round variables
    def prepare_for_next_round(self):
        print "prepare_for_next_round(self) "
        self.current_game.current_round += 1

        self.player_bids_for_current_round = []
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None

        self.sub_rounds_played = 0
        self.winning_sub_round_card = None
        self.winer_for_sub_round = None
        self.cards_played_for_sub_round = []
        self.zero_point_players = []

        # TODO: Should James have added self.player_bid_queue.clear() to this?
        self.player_bid_queue.clear()


    def remove_card_from_players_hand(self, current_player_id, card_to_remove):
        print "remove_card_from_players_hand(self, current_player_id, card_to_remove) "
        print "  current_player_id: ",current_player_id
        print "  card_to_remove: ",card_to_remove

        idx_of_card_to_remove = None
        for player in self.current_game.players:
            if player.id == current_player_id:
                #we found the player, now remove the appropriate card from his/her hand
                for idx, card in enumerate(player.cards_in_hand):
                    if card == card_to_remove:
                        idx_of_card_to_remove = idx
                player.cards_in_hand.pop(idx_of_card_to_remove)
                if len(player.cards_in_hand) > 0:
                    self.display_cards_for_player_in_pm(player.id, player.cards_in_hand)

    # TODO: Modify this to make Drumpf! a reality
    def determine_winner_for_sub_round(self, card):
        print "determine_winner_for_sub_round(self, card) "
        self.winning_sub_round_card = None
        print("  Players in game: {}".format(self.users_in_game))
        print("   Cards played: {}".format(self.cards_played_for_sub_round))
        num_cards_played = len(self.cards_played_for_sub_round)

        card_value_sub_round = None
        card_suit_sub_round = None

        if len(self.cards_played_for_sub_round[0]) == 2:
            card_value_sub_round = str(self.cards_played_for_sub_round[0][0])
            card_suit_sub_round = self.cards_played_for_sub_round[0][1]
        else:
            card_value_sub_round = str(self.cards_played_for_sub_round[0])
            card_suit_sub_round = None
        print "  card_value_sub_round: ",card_value_sub_round
        print "  card_suit_sub_round: ",card_suit_sub_round
        # everyone has played VM cards, first person to play one wins
        if "VM:" in ([self.cards_played_for_sub_round for _ in range(num_cards_played)]):
            print("  Everyone played visible minority cards this sub-round. First player wins.")
            self.winning_sub_round_card = self.cards_played_for_sub_round[0]
            print "  Winning sub-round card: ",self.winning_sub_round_card
            self.winner_for_sub_round = self.player_turn_queue_reference[0]
            print "  player_turn_queue_reference: ",self.winner_for_sub_round
            return
        # Russian Blackmail card wins in every situation
        elif card_value_sub_round.startswith("T: russian"):
            print("  First player played a Russian Blackmail card, he/she wins.")
            self.winning_sub_round_card = card_value_sub_round
            print "  Winning sub-round card: ",self.winning_sub_round_card
            self.winner_for_sub_round = self.player_turn_queue_reference[0]
            print "  player_turn_queue_reference: ",self.winner_for_sub_round
            return
        else:
            #we have to iterate over the cards to determine the winner for the sub-round
            winning_card = None
            trump_suit = self.current_game.current_round_trump_suit
            print  "  trump_suit: ",trump_suit
            card_value = None
            card_suit = None
            self.shower_card_holder = None
            visited = False # keeps track of the case of pussy/ivanka/nasty cards all being played same round
            for idx, card in enumerate(self.cards_played_for_sub_round):
                if len(card) == 2:
                    card_value = str(card[0])
                    card_suit = card[1]
                else:
                    card_value = str(card)
                    card_suit = None
                current_player = self.player_turn_queue_reference[idx]
                print "  current_player: ",current_player

                # handle Tremendous cards and Drumpf cards
                if card_value.startswith("T:") or card_value.startswith("D:"):
                    # golden shower card means player wins 3 lies for the round
                    if card_value.startswith("T: shower"):
                        print "  handling {} card...".format(card_value)
                        self.shower_card_holder = current_player
                        print "    shower_card_holder: {}".format(self.shower_card_holder)
                        continue
                    # russian blackmail card always wins sub-round
                    elif card_value.startswith("T: russian"):
                        print "  handling {} card...".format(card_value)
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                        print "  {} card wins".format(card)
                        print "  player {} wins".format(current_player)
                        return

                    # comey card steals Clinton's Email Server card
                    elif card_value.startswith("D: clinton"):
                        print "  handling {} card...".format(card_value)
                        if "T: comey" in self.cards_played_for_sub_round:
                            print "    {} card played in round".format(card_value)
                            comey_card_idx = self.cards_played_for_sub_round.index("T: comey")
                            if idx < comey_card_idx:
                                print "    {} card steals {} card...".format(self.cards_played_for_sub_round[comey_card_idx],card_value)
                                self.winning_sub_round_card = self.cards_played_for_sub_round[comey_card_idx]
                                self.winner_for_sub_round = self.player_turn_queue_reference[comey_card_idx]
                                print "  {} card wins".format(self.winning_sub_round_card)
                                print "  player {} wins".format(self.winner_for_sub_round)
                                return
                            else:
                                self.winning_sub_round_card = card
                                self.winner_for_sub_round = current_player
                                print "  {} card wins".format(card)
                                print "  player {} wins".format(current_player)
                                return
                        elif "T: nasty" in self.cards_played_for_sub_round:
                            nasty_card_idx = self.cards_played_for_sub_round.index("T: nasty")
                            if idx < nasty_card_idx:
                                print "  {} card negates {} card...".format(self.cards_played_for_sub_round[nasty_card_idx],card_value)
                                continue
                            else:
                                print "  {} card wins".format(card)
                                self.winning_sub_round_card = card
                                self.winner_for_sub_round = current_player
                                print "  {} card wins".format(card)
                                print "  player {} wins".format(current_player)
                                return
                        else:
                            self.winning_sub_round_card = card
                            self.winner_for_sub_round = current_player
                            print "  {} card wins".format(card)
                            print "  player {} wins".format(current_player)
                            return

                    # The Wall card can be usurped by the Bad Hombres
                    elif card_value.startswith("D: wall"):
                        print "  handling {} card...".format(card_value)
                        if "VM: hombres" in self.cards_played_for_sub_round:
                            print "  *VM: hombres card present..."
                            hombres_card_idx = self.cards_played_for_sub_round.index("VM: hombres")
                            if idx < hombres_card_idx:
                                self.winning_sub_round_card = self.cards_played_for_sub_round[hombres_card_idx]
                                self.winner_for_sub_round = self.player_turn_queue_reference[hombres_card_idx]
                                print "  {} card wins".format(self.winning_sub_round_card)
                                print "  player {} wins".format(self.winner_for_sub_round)
                                return
                            else:
                                self.winning_sub_round_card = card
                                self.winner_for_sub_round = current_player
                                print "  {} card wins".format(self.winning_sub_round_card)
                                print "  player {} wins".format(self.winner_for_sub_round)
                                return
                        elif "T: nasty" in self.cards_played_for_sub_round:
                            nasty_card_idx = self.cards_played_for_sub_round.index("T: nasty")
                            if idx < nasty_card_idx:
                                print "  {} card negates {} card...".format(self.cards_played_for_sub_round[nasty_card_idx],card_value)
                                continue
                            else:
                                self.winning_sub_round_card = card
                                self.winner_for_sub_round = current_player
                                print "  {} card wins".format(card)
                                print "  player {} wins".format(self.winner_for_sub_round)
                                return
                        else:
                            self.winning_sub_round_card = card
                            self.winner_for_sub_round = current_player
                            print "  {} card wins".format(card)
                            print "  player {} wins".format(self.winner_for_sub_round)
                            return
                    # the regular old Drumpf cards
                    elif card_value.startswith("D: pussy") or card_value.startswith("D: ivanka"):
                        print "  handling {} card...".format(card_value)
                        # the non-negated Drumpf wins
                        if visited:
                            self.winning_sub_round_card = card
                            self.winner_for_sub_round = current_player
                            print "  {} card wins".format(self.winning_sub_round_card)
                            print "  player {} wins".format(self.winner_for_sub_round)
                            return
                        else:
                            if "T: nasty" in self.cards_played_for_sub_round:
                                nasty_card_idx = self.cards_played_for_sub_round.index("T: nasty")
                                if idx < nasty_card_idx:
                                    visited = True
                                    print "  {} card negates {} card...".format(self.cards_played_for_sub_round[nasty_card_idx],card_value)
                                    continue
                                else:
                                    self.winning_sub_round_card = card
                                    self.winner_for_sub_round = current_player
                                    print "  {} card wins".format(self.winning_sub_round_card)
                                    print "  player {} wins".format(self.winner_for_sub_round)
                                    return
                            else:
                                self.winning_sub_round_card = card
                                self.winner_for_sub_round = current_player
                                print "  {} card wins".format(self.winning_sub_round_card)
                                print "  player {} wins".format(self.winner_for_sub_round)
                                return

                    elif card_value.startswith("T: nasty") or card_value.startswith("T: comey"):
                        print "  handling {} card...".format(card_value)
                        continue

                elif card_value[0:3] == "VM:":
                    print "  handling {} card...".format(card_value)
                    if "muslims" in card_value or "thieves" in card_value or "hombres" in card_value:
                        continue

                    # if "hombres" in card_value:
                    #     if any("wall" in s for s in self.cards_played_for_sub_round):
                    #         self.winning_sub_round_card = card
                    #         self.winner_for_sub_round = current_player
                    #         print "  {} card wins".format(self.winning_sub_round_card)
                    #         print "  player {} wins".format(self.winner_for_sub_round)
                    #     return

                    if "blacks" in card_value:
                        self.zero_point_players.append(current_player)
                        return
                    return

                elif card_suit == trump_suit:
                    print "  card_suit == trump_suit <-> {} == {}".format(card_suit,trump_suit)
                    # if self.winning_sub_round_card != None:
                    if self.winning_sub_round_card == None:
                        print "  self.winning_sub_round_card == ", self.winning_sub_round_card
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                        print "  {} card wins".format(self.winning_sub_round_card)
                        print "  player {} wins".format(self.winner_for_sub_round)

                    elif self.winning_sub_round_card[1] == trump_suit:
                        print "  self.winning_sub_round_card[1] == trump_suit <-> {} == {}".format(self.winning_sub_round_card[1],trump_suit)
                        if DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.winning_sub_round_card):
                            print "  trump suit played beats previous trump suit"
                            #trump suit played beats previous trump suit
                            self.winning_sub_round_card = card
                            self.winner_for_sub_round = current_player
                            print "  {} card wins".format(self.winning_sub_round_card)
                            print "  player {} wins".format(self.winner_for_sub_round)
                    else:
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                        print "  {} card wins".format(self.winning_sub_round_card)
                        print "  player {} wins".format(self.winner_for_sub_round)
                elif card_suit == self.leading_suit:
                    print "  card_suit == self.leading_suit <-> {} == {}".format(card_suit,self.leading_suit)
                    if self.winning_sub_round_card == None:
                        print "  no self.winning_sub_round_card"
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                        print "  {} card wins".format(self.winning_sub_round_card)
                        print "  player {} wins".format(self.winner_for_sub_round)
                    elif DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.winning_sub_round_card):
                        print "  the card index of {} is greater than the index of the winning sub-round card ({})".format(card,self.winning_sub_round_card)
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                        print "  {} card wins".format(self.winning_sub_round_card)
                        print "  player {} wins".format(self.winner_for_sub_round)

        # TODO: remember to reset all the sub-round variables for the next sub-round

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


    def handle_private_message(self, command, user_id):
        print "handle_private_message(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id
        response = ""
        if len(self.player_trump_card_queue):
            self.handle_trump_suit_selection(command, user_id)

        elif len(self.player_bid_queue):
            self.handle_player_bid(command, user_id)

        elif len(self.player_turn_queue):
            self.handle_player_turn(command, user_id)


    def parse_slack_output(self, slack_rtm_output):
        #
        # print " parse_slack_output(self, slack_rtm_output) "
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and AT_BOT in output['text']:
                    # return text after the @ mention, whitespace removed
                    #example return: (u'hi', u'C2F154UTE', )
                    return output['text'].split(AT_BOT)[1].strip().lower(), \
                           output['channel'], output['user']
        return None, None, None

    def get_bids_from_players(self, current_round, players):
        print "get_bids_from_players(self, current_round, players) "
        print "  current_round: ", current_round
        print "  players: ", players

        self.player_bid_queue = deque([player.id for player in players])
        self.player_turn_queue = deque([player.id for player in players])
        #the player after the dealer should be first to bid, so we rotate the queue
        self.player_bid_queue.rotate(-1)
        self.player_turn_queue.rotate(-1)
        self.player_turn_queue_reference = copy.copy(self.player_turn_queue)
        self.users_in_game.rotate(-1)

        # #DEBUGGING REMOVE THIS AFTER TESTING
        # self.player_bid_queue.clear()
        # self.player_bids_for_current_round = [1 ,1]
        # self.message_main_game_channel("_DEBUG MODE: Automatic bidding, < 3 players can play_")
        # self.private_message_user(self.player_turn_queue[0], "Play a card `index`")
        #DEBUGGING

        slack_client.api_call(
            "chat.postMessage",
            channel=self.player_bid_queue[0],
            text="What's your bid for the round?",
            as_user=True
        )

    def prompt_dealer_for_trump_suit(self, player_id):
        print "prompt_dealer_for_trump_suit(self, player_id) "
        print "  player_id: ", player_id
        self.player_trump_card_queue.append(player_id)
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="please select index for trump suit \n `0`[:diamonds:]   `1`[:clubs:]   `2`[:hearts:]   `3`[:spades:]",
            as_user=True
        )

    def get_readable_list_of_players(self):
        print "get_readable_list_of_players(self) "
        #TODO refactor this with less mumbojumbo
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
        print "  cards: ", cards

        formatted_cards = helper_functions.format_cards_to_emojis(cards)
        self.attachments = None
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="Your card(s): {}".format(formatted_cards),
            as_user=True, attachments=self.attachments
        )
        # for card in cards:
        #     if card in DrumpfGame.drumpf_deck_special:
        #         image_url = "http://cjbrogers.com/drumpf/images/"+card+".png"
        #         self.attachments = [{"title": card, "image_url": image_url}]
        #         slack_client.api_call(
        #             "chat.postMessage",
        #             channel=player_id,
        #             as_user=True, attachments=self.attachments
        #         )
        #     else:
        #         self.attachments = None
        #         slack_client.api_call(
        #             "chat.postMessage",
        #             channel=player_id,
        #             as_user=True, attachments=self.attachments
        #         )

    def announce_trump_card(self, trump_card):
        print "announce_trump_card(self, trump_card) "
        print "  trump_card: ",trump_card

        self.message_main_game_channel(">>>*Round {}* \n The trump card is: {} \n".format(
            self.current_game.current_round,
            helper_functions.emojify_card(trump_card)), attachments=self.attachments)

        self.message_main_game_channel(">>>_Sub-Round {}_".format(self.sub_rounds_played + 1))

    #takes an array of player_ids and the channel the game request originated from
    def play_game_of_drumpf_on_slack(self, players, channel):
        print "play_game_of_drumpf_on_slack(self, players, channel) "
        print "  players: ", players
        print "  channel: ", channel

        player_objects = []
        for player_id in players:
            player_objects.append(DrumpfGame.Player(player_id))
        game = DrumpfGame.Game(player_objects, bot)
        game.play_round()

    #Restarts the current program.
    def restart_program(self):
        python = sys.executable
        os.execl(python, python, * sys.argv)

if __name__ == "__main__":
    bot = DrumpfBot()
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    #grab user list and converts it to to a dict of ids to usernames
    api_call = slack_client.api_call("users.list")

    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            bot.user_ids_to_username[user['id']] = user['name']

        channels = slack_client.api_call("channels.list").get('channels')
        for channel in channels:
            bot.channel_ids_to_name[channel['id']] = channel['name']

    if slack_client.rtm_connect():
        print("drumpfbot connected and running!")

        while True:
            command, channel, user = bot.parse_slack_output(slack_client.rtm_read())
            if command and channel:
                if channel not in bot.channel_ids_to_name.keys():
                    #this (most likely) means that this channel is a PM with the bot
                    bot.handle_private_message(command, user)
                else:
                    bot.handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
