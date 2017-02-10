# -*- coding: utf-8 -*-
import os
import time
import copy

from slackclient import SlackClient
from collections import defaultdict
from collections import deque

import drumpfgame as DrumpfGame
import helper_functions

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
        self.main_channel_id = 'C41Q1H4BD' #TODO make this dynamic
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

        self.attachments = None

    def handle_command(self, command, channel, user_id):
        attachments = None
        #TODO restrict the channel this is in
        username = self.user_ids_to_username[user_id] #user who sent the message

        #TODO this response can come from a random array of responses to gibberish
        response = "Wrong! I only respond to tremendous, I mean, ya know, real bigly commands."

        if command.lower().startswith("debug"):
            self.users_in_game.append('U3MP47XAB') #James U3MP47XAB
            self.users_in_game.append('U3LCLSTA5') #Roberto U3LCLSTA5 Alex U3LNCN0F3 Gordi-bot U42H6H9L5 Slackbot USLACKBOT drumpfbot U41R44L82
            response = ">>>Starting a new game of Drumpf with players: \n" + self.get_readable_list_of_players()
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text=response, as_user=True)
            self.play_game_of_drumpf_on_slack(self.users_in_game, channel)
            return

        if command.lower().startswith("create game"):
            if len(self.users_in_game) == 0:
                response = "<@{}> Wants to play a game of drumpf! Type `@drumpfbot add me` to play.".format(username)
                self.users_in_game.append(user_id)
            else:
                response = "There's already a game being made, say `add me` if you want in."

        if command.lower().startswith("cancel"):
            response = "Okay, game cancelled."
            self.users_in_game.clear()

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
             #TODO this should be minimum for 3 players.
             #TODO is there a max number of players?
            if len(self.users_in_game) == 0:
                response = "No game exists yet. Try `create game`"

            elif len(self.users_in_game) < 2:
                response = "There aren't enough players yet (minimum 4). Users can say `add me` to be added to the game."
            else:
                response = ">>>Starting a new game of Drumpf with players: \n" + self.get_readable_list_of_players()
                slack_client.api_call("chat.postMessage", channel=channel,
                                      text=response, as_user=True)
                self.play_game_of_drumpf_on_slack(self.users_in_game, channel)
                return #have to do this because we want the "new game" message to come before the trump card announcement

        if command.lower().startswith("commands") or command.lower().startswith("help"):
            response = ">>>Certainly, my liege. The available commands are: \n\n" \
            "*[add me]*\tAdd yourself to the game queue.\n" \
            "*[bigly]*\tIt's a word.\n" \
            "*[cancel]*\tStop the current game.\n" \
            "*[card rules]*\tView the card values.\n" \
            "*[commands]*\tView available commands.\n" \
            "*[create game]*\tLet Slack know you want to play a game. Players reply '<@drumpfbot> add me' if they wish to join.\n"\
            "*[debug]*\tStart a game in debug mode. Bidding is automatic.\n" \
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

        if command.lower().startswith("card rules"):
            response = ">>>Here's the card deck composition: \n"
            image_url = "https://s30.postimg.org/r28wxm89t/cards.png"
            attachments = [{"title": "Card Deck Composition", "image_url": image_url}]

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True, attachments=attachments)

    def handle_trump_suit_selection(command, user_id):
        response = ""
        current_username = self.user_ids_to_username[self.player_trump_card_queue[0]]
        #we're waiting for a user to select a trump card
        if user_id != self.player_trump_card_queue[0]:
            response = "Waiting for <@{}> to select a trump suit"
        elif user_id == self.player_trump_card_queue:
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

        self.private_message_user(user_id, response)

    def get_card_being_played(self, user_id, index): # -> ex. ['K', 'spades']
        for user_object in self.current_game.players:
            if user_object.id == user_id:
                print(user_object.cards_in_hand)
                if index > len(user_object.cards_in_hand):
                    return None
                else:
                    return user_object.cards_in_hand[index]

    def handle_player_bid(self, command, user_id):
        current_username = self.user_ids_to_username[self.player_bid_queue[0]]
        #we're waiting for the first player in queue to bid
        if user_id != self.player_bid_queue[0]:
            response = "We're still waiting on <@{}> to bid.".format(current_username)
        elif user_id == self.player_bid_queue[0]:
            #expected user to bid
            try:
                print self.current_game.current_round
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
        response = ""
        current_username = self.user_ids_to_username[self.player_turn_queue[0]]
        print("User sending message: {}".format(self.user_ids_to_username[user_id]  ))
        #waiting for first player after dealer to play a card
        if user_id != self.player_turn_queue[0]:
            response = "Waiting for <@{}> to play a card.".format(current_username)
        elif user_id == self.player_turn_queue[0]:
            print('Received input from expected player: {}'.format(current_username))
            #validate the int(command) index selected is within the range of cards in hand
            if int(command) >= 0 and int(command) < self.current_game.current_round:

                print("Selected a valid card index")
                card_being_played = self.get_card_being_played(user_id, int(command))
                if card_being_played == None:
                    self.private_message_user(user_id, "That's not a valid card index")
                    return
                #otherwise valid card played
                if self.leading_suit != None:
                    print("Sub-round trump suit: {}".format(self.leading_suit))
                    #a drumpf or a jester is always a valid play
                    if card_being_played == "drumpf" or card_being_played == "jester":
                        self.handle_valid_card_played(card_being_played)
                    elif self.leading_suit == "Any":
                        #a drumpf was played as the first card
                        #players are free to play whatever they want
                        self.handle_valid_card_played(card_being_played)
                    elif card_being_played[1] == self.leading_suit:
                        #card played same suit as sub_round_suit
                        self.handle_valid_card_played(card_being_played)
                    elif self.player_hand_contains_suit(user_id, self.leading_suit) == False:
                        #any card is valid, because player doesn't have the initial suit
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.private_message_user(user_id, "Sorry, you can't play that card")
                elif self.leading_suit == None:
                    print("There is no sub-round trump suit")
                    if card_being_played == "drumpf":
                        print("{} played a Drumpf".format(current_username))
                        self.leading_suit = "Any"
                        self.handle_valid_card_played(card_being_played)
                    elif card_being_played == "jester":
                        print("{} played a Jester".format(current_username))
                        #the sub round suit stays None until a player plays a suited card
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.leading_suit = card_being_played[1]
                        print("Sub-round trump suit set to {}".format(card_being_played[1]))
                        self.handle_valid_card_played(card_being_played)
            else:
                response = "That wasn't a valid card index."
        self.private_message_user(user_id, response)

    def player_hand_contains_suit(self, user_id, suit):
        print("Checking if player hand contains expected suit, {}".format(self.leading_suit))
        for user_object in self.current_game.players:
            if user_object.id == user_id:
                for card in user_object.cards_in_hand:
                    if card != "drumpf" and card != "jester":
                        if card[1] == suit:
                            return True
        return False

    def handle_valid_card_played(self, card):
        player_who_played_card = self.user_ids_to_username[self.player_turn_queue[0]]
        self.remove_card_from_players_hand(self.player_turn_queue[0], card)
        card_emoji = helper_functions.emojify_card(card)

        # if card in DrumpfGame.drumpf_deck_special:
        #     self.message_main_game_channel("><@{}> played:".format(player_who_played_card))
        #     image_url = "http://cjbrogers.com/drumpf/images/"+card+".png"
        #     self.attachments = [{"title": card, "image_url": image_url}]
        #     slack_client.api_call(
        #         "chat.postMessage",
        #         channel=self.main_channel_id,
        #         as_user=True, attachments=self.attachments
        #     )
        # else:
        #     self.attachments = None
        #     self.message_main_game_channel("><@{}> played {}".format(player_who_played_card, card_emoji))

        self.message_main_game_channel("><@{}> played {}".format(player_who_played_card, card_emoji))
        self.cards_played_for_sub_round.append(card)
        print("Cards played for sub-round: {}".format(self.cards_played_for_sub_round))
        self.player_turn_queue.popleft()
        print("Player turn queue: {}".format(self.player_turn_queue))
        if len(self.player_turn_queue) == 0:
            self.sub_rounds_played += 1
            print(">Everyone played, time to determine winner for sub-round")
            self.determine_winner_for_sub_round()
            self.player_points_for_round[self.winner_for_sub_round] += 1
            self.message_main_game_channel(">*<@{}> won this sub-round with a {}*".format(
                self.winner_for_sub_round, helper_functions.emojify_card(self.winning_sub_round_card)), attachments=self.attachments)
            #reset all sub-round variables
            self.leading_suit = None
            self.cards_played_for_sub_round = []

            if self.sub_rounds_played == self.current_game.current_round:
                print("Sub-rounds over, time to tally points and display them")
                self.calculate_and_display_points_for_players()
                self.winner_for_sub_round = None
            elif self.sub_rounds_played < self.current_game.current_round:
                self.message_main_game_channel(">_Sub-Round {}_".format(self.sub_rounds_played + 1))
                #initialize another turn queue cause there are more cards to play
                self.player_turn_queue = copy.copy(self.users_in_game)
                while self.player_turn_queue[0] != self.winner_for_sub_round:
                    print("Rotating player turn queue")
                    #rotate player_turn_queue until the first player is the one who won
                    self.player_turn_queue.rotate(1)
                self.player_turn_queue_reference = copy.copy(self.player_turn_queue)
                self.winner_for_sub_round = None
                self.private_message_user(self.player_turn_queue[0], "Play a card `index`")
        else:
            self.private_message_user(self.player_turn_queue[0], "Play a card `index`")

    def calculate_and_display_points_for_players(self):
        self.message_main_game_channel("*Round {} over!* _calculating points..._".format(self.current_game.current_round))
        for idx, player_id in enumerate(self.users_in_game):
            current_players_bid = self.player_bids_for_current_round[idx]
            points_off_from_bid = abs(current_players_bid - self.player_points_for_round[player_id])
            if points_off_from_bid == 0:
                #The player got his/her bid correctly
                self.game_scorecard[player_id] += (50 + 25 * current_players_bid)
            else:
                #player loses 10-points for every point above or below bid
                self.game_scorecard[player_id] -= 25 * points_off_from_bid
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
        pass

    def prepare_for_next_round(self):
        self.current_game.current_round += 1

        self.player_bids_for_current_round = []
        self.player_points_for_round = defaultdict(int)
        self.leading_suit = None

        self.sub_rounds_played = 0
        self.winning_sub_round_card = None
        self.winer_for_sub_round = None
        self.cards_played_for_sub_round = []
        #clears all round and sub-round variables

    def remove_card_from_players_hand(self, current_player_id, card_to_remove):
        idx_of_card_to_remove = None
        for player in self.current_game.players:
            if player.id == current_player_id:
                print('this got called')
                #we found the player, now remove the appropriate card from his/her hand
                for idx, card in enumerate(player.cards_in_hand):
                    if card == card_to_remove:
                        idx_of_card_to_remove = idx
                player.cards_in_hand.pop(idx_of_card_to_remove)
                if len(player.cards_in_hand) > 0:
                    self.display_cards_for_player_in_pm(player.id, player.cards_in_hand)


    def determine_winner_for_sub_round(self):
        self.winning_sub_round_card = None
        print("Players in game: {}".format(self.users_in_game))
        print("Cards played: {}".format(self.cards_played_for_sub_round))
        num_cards_played = len(self.cards_played_for_sub_round)
        if self.cards_played_for_sub_round == ["jester" for _ in range(num_cards_played)]:
            print("Everyone played jesters this sub-round. First player wins.")
            self.winning_sub_round_card = "jester"
            self.winner_for_sub_round = self.player_turn_queue_reference[0]
            return
        elif self.cards_played_for_sub_round[0] == "drumpf":
            print("First player played a Drumpf, he/she wins.")
            self.winning_sub_round_card = "drumpf"
            self.winner_for_sub_round = self.player_turn_queue_reference[0]
            return
        else:
            #we have to iterate over the cards to determine the winner for the sub-round
            winning_card = None
            trump_suit = self.current_game.current_round_trump_suit
            for idx, card in enumerate(self.cards_played_for_sub_round):
                current_player = self.player_turn_queue_reference[idx]
                if card == "drumpf":
                    #first drumpf played wins, regardless of all other hands
                    self.winning_sub_round_card = card
                    self.winner_for_sub_round = current_player
                    return
                elif card[1] == trump_suit:
                    if self.winning_sub_round_card[1] == trump_suit:
                        if DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.winning_sub_round_card):
                            #trump suit played beats previous trump suit
                            self.winning_sub_round_card = card
                            self.winner_for_sub_round = current_player
                    else:
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                elif card[1] == self.leading_suit:
                    if self.winning_sub_round_card == None:
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player
                    elif DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.winning_sub_round_card):
                        self.winning_sub_round_card = card
                        self.winner_for_sub_round = current_player


        #remember to reset all the sub-round variables for the next sub-round

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
        response = ""
        if len(self.player_trump_card_queue):
            # self.handle_trump_suit_selection(command, user_id)
            self.handle_trump_suit_selection(command, user_id)

        elif len(self.player_bid_queue):
            self.handle_player_bid(command, user_id)

        elif len(self.player_turn_queue):
            self.handle_player_turn(command, user_id)


    def parse_slack_output(self, slack_rtm_output):
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

        # slack_client.api_call(
        #     "chat.postMessage",
        #     channel=self.player_bid_queue[0],
        #     text="What's your bid for the round?",
        #     as_user=True
        # )

    def prompt_dealer_for_trump_suit(self, player_id):
        self.player_trump_card_queue.append(player_id)
        slack_client.api_call(
            "chat.postMessage",
            channel=player_id,
            text="please select index for trump suit \n `0`[:diamonds:]   `1`[:clubs:]   `2`[:hearts:]   `3`[:spades:]",
            as_user=True
        )

    def get_readable_list_of_players(self):
        #TODO refactor this with less mumbojumbo
        player_names = []
        printable_player_names = []
        for player_id in self.users_in_game:
            player_names.append(self.user_ids_to_username[player_id])
        for idx, player_name in enumerate(player_names):
            printable_player_names.append("{}) <@{}>".format(idx + 1, player_name))
        return (' \n ').join(printable_player_names)

    def display_cards_for_player_in_pm(self, player_id, cards):
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
        # for card in DrumpfGame.drumpf_deck_special:
        # if trump_card in DrumpfGame.drumpf_deck_special:
        #     image_url = "http://cjbrogers.com/drumpf/images/"+trump_card+".png"
        #     self.attachments = [{"title": trump_card, "image_url": image_url}]
        # else:
        #     self.attachments = None

        self.message_main_game_channel(">>>*Round {}* \n The trump card is: {} \n".format(
            self.current_game.current_round,
            helper_functions.emojify_card(trump_card)), attachments=self.attachments)

        self.message_main_game_channel(">>>_Sub-Round {}_".format(self.sub_rounds_played + 1))

    #takes an array of player_ids and the channel the game request originated from
    def play_game_of_drumpf_on_slack(self, players, channel):
        player_objects = []
        for player_id in players:
            player_objects.append(DrumpfGame.Player(player_id))
        game = DrumpfGame.Game(player_objects, bot)
        game.play_round()


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
                print 'command: ', command
                if channel not in bot.channel_ids_to_name.keys():
                    #this (most likely) means that this channel is a PM with the bot
                    bot.handle_private_message(command, user)
                else:
                    bot.handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
