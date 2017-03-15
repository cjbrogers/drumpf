from slackclient import SlackClient
from slacker import Slacker
import helper_functions
from collections import deque
import copy
import models
import math


class Bid():

    def __init__(self, bot, score):
        self.bot = bot
        self.slack_client = self.bot.slack_client
        self.slack = self.bot.slack
        self.score = score
        self.slack_client = self.bot.slack_client

    def present_bid_buttons(self, player_id):
        """
        Presents the bidding buttons to the user (max 5 at a time due to Slack's API restrictions)

        Args:
                [player_id] the player's id of whom to post the bid buttons to
        """
        print "present_bid_buttons(self, player_id)"
        button_indices = []
        for player in self.bot.current_game.players:
            if player.id == player_id:
                for idx, card in enumerate(player.cards_in_hand):
                    button_indices.append(idx)
                button_indices.append(len(player.cards_in_hand))
        self.bot.first_set = False
        button_set = []
        no_button_sets = int(math.ceil(len(button_indices) / 5.0))
        # TODO: clean this up with new no_button_sets logic
        if len(button_indices) > 5:
            for idx in button_indices:
                if idx == 0:
                    self.bot.first_set = True
                    button_set.append(idx)
                elif (idx % 5) != 0:
                    button_set.append(idx)
                elif (idx % 5) == 0: # e.g. 6 buttons, so post first 5
                    attachments = helper_functions.buttonify_bids(
                        button_set, self.bot.first_set, no_button_sets)
                    resp = self.slack_client.api_call("chat.postMessage",
                                                      channel=player_id,
                                                      as_user=True,
                                                      attachments=attachments)
                    ts_no_remainder = resp['ts']
                    event = "bid_buttons_" + str(idx)

                    bot_im_id = models.get_bot_im_id(
                        player_id, self.bot.team_id)
                    models.log_message_ts(
                        ts_no_remainder, bot_im_id, event, self.bot.team_id)
                    self.bot.first_set = False
                    button_set[:] = []
                    button_set.append(idx)
                if (idx + 1) == len(button_indices): # e.g. 6th button, post it
                    attachments = helper_functions.buttonify_bids(
                        button_set, self.bot.first_set, no_button_sets)
                    resp = self.slack_client.api_call("chat.postMessage",
                                                      channel=player_id,
                                                      as_user=True,
                                                      attachments=attachments)
                    ts_remainder = resp['ts']
                    event = "bid_buttons_" + str(len(button_indices))
                    bot_im_id = models.get_bot_im_id(
                        player_id, self.bot.team_id)
                    models.log_message_ts(
                        ts_remainder, bot_im_id, event, self.bot.team_id)
                    button_set[:] = []
        else:
            self.bot.first_set = True
            attachments = helper_functions.buttonify_bids(
                button_indices, self.bot.first_set, no_button_sets)
            resp = self.slack_client.api_call("chat.postMessage",
                                              channel=player_id,
                                              as_user=True,
                                              attachments=attachments)
            ts = resp['ts']
            event = "bid_buttons_" + str(len(button_indices))
            bot_im_id = models.get_bot_im_id(player_id, self.bot.team_id)
            models.log_message_ts(ts, bot_im_id, event, self.bot.team_id)
            self.bot.first_set = False
        return

    def handle_player_bid(self, command, user_id):
        """
        Deals with the logic for handling player bidding
        Args: [command] the bid command (int)
        Args: [user_id] the id of the user in question
        """
        print "handle_player_bid(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id
        print "  player: ", self.bot.user_ids_to_username[user_id]

        current_username = self.bot.user_ids_to_username[self.bot.player_bid_queue[0]]
        # we're waiting for the first player in queue to bid
        if user_id != self.bot.player_bid_queue[0]:
            print "  We're still waiting on <@{}> to bid.".format(current_username)
            response = "We're still waiting on <@{}> to bid.".format(
                current_username)
        elif user_id == self.bot.player_bid_queue[0]:
            # expected user to bid
            try:
                if 0 > int(command) > self.bot.current_game.current_round:
                    print "  You can't bid that amount you turkey!"
                    response = "You can't bid that amount you turkey!"
                else:
                    # valid bid
                    print "  `Bid recorded!`"
                    self.bot.player_bids_for_current_round[user_id] = int(
                        command)
                    msg = "><@{}> bids `{}`.\n".format(
                        current_username, int(command))
                    print "  ", msg
                    self.score.build_scoreboard(msg)
                    self.score.update_scoreboard(self.bot.scoreboard)
                    self.score.pm_users_scoreboard(self.bot.scoreboard)

                    self.bot.player_bid_queue.popleft()
                    if len(self.bot.player_bid_queue) == 0:
                        # everyone bidded, time to play sub_round
                        for player in self.bot.current_game.players:
                            if player.id == self.bot.player_turn_queue[0]:
                                msg = "Play a card."
                                self.bot.display_cards_for_player_in_pm(
                                    self.bot.player_turn_queue[0], player.cards_in_hand, msg)
                        return

                    else:  # get the next player's bid
                        msg = "What's your bid for the round?"
                        print "  ", msg
                        self.present_bid_buttons(self.bot.player_bid_queue[0])
                        return
            except Exception as e:
                raise

        self.bot.private_message_user(user_id, response)

    def get_bids_from_players(self, current_round, players):
        """
        Gets the bids of the players
        Args: [current_round] the current round of the game
        Args: [players] the players in the game
        """
        print "get_bids_from_players(self, current_round, players) "
        print "  current_round: ", current_round
        print "  players: ", players

        self.bot.player_bid_queue = deque([player.id for player in players])
        self.bot.player_turn_queue = deque([player.id for player in players])
        # the player after the dealer should be first to bid, so we rotate the
        # queue
        print "  *rotating self.bot.player_bid_queue; self.bot.player_turn_queue; self.bot.users_in_game"
        self.bot.player_bid_queue.rotate(-1)
        self.bot.player_turn_queue.rotate(-1)
        self.bot.player_turn_queue_reference = copy.copy(
            self.bot.player_turn_queue)
        self.bot.users_in_game.rotate(-1)
        if not self.bot.drumpfmendous_card_first:
            self.present_bid_buttons(self.bot.player_bid_queue[0])
