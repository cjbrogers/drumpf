import helper_functions
from slackclient import SlackClient
from slacker import Slacker

slack_client = SlackClient(helper_functions.get_slack_client())
slack = Slacker(helper_functions.get_slack_client())

class DisplayMessages():

    def __init__(self,bot,bid,trump,round_):
        self.bot = bot
        self.bid = bid
        self.trump = trump
        self.round = round_

    def message_main_game_channel(self, message, attachments=None):
        """Posts a message to the main game channel

        Args:
            [message] (str) the message to post
            [attachments] (list) a list of attachments to append to the message -optional, defaults to None
        Returns:
        """
        slack_client.api_call(
            "chat.postMessage",
            channel=self.bot.main_channel_id,
            text=message,
            as_user=True, attachments=attachments
        )

    def private_message_user(self, user_id, message, attachments=None):
        """Posts a private message to a user channel

        Args:
            [user_id] (str) id of the player
            [message] (str) the message to post
            [attachments] (list) a list of attachments to append to the message -optional, defaults to None
        Returns:
        """
        slack_client.api_call(
            "chat.postMessage",
            channel=user_id,
            text=message,
            as_user=True, attachments=attachments
        )

    def handle_private_message(self,command,user_id):
        """Controls how a private message incoming from a user is handled

        Args:
            [command] (str) incoming command to handle
            [user_id] (str) the id of the player
        Returns:
        """
        print "handle_private_message(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id

        response = ""

        print "  **$$**len(self.bot.player_trump_card_queue): {}".format(len(self.bot.player_trump_card_queue))
        print "  **$$**self.bot.player_trump_card_queue: {}".format(self.bot.player_trump_card_queue)

        print "  **$$**len(self.bot.player_bid_queue): {}".format(len(self.bot.player_bid_queue))
        print "  **$$**self.bot.player_bid_queue: {}".format(self.bot.player_bid_queue)

        print "  **$$**len(self.bot.player_turn_queue): {}".format(len(self.bot.player_turn_queue))
        print "  **$$**self.bot.player_turn_queue: {}".format(self.bot.player_turn_queue)

        if len(self.bot.player_trump_card_queue):
            print "  len(self.bot.player_trump_card_queue)"
            self.trump.handle_trump_suit_selection(command, user_id)

        elif len(self.bot.player_bid_queue):
            print "  len(self.bot.player_bid_queue)"
            self.bid.handle_player_bid(command, user_id)

        elif len(self.bot.player_turn_queue):
            print "  len(self.bot.player_turn_queue)"
            self.round.handle_player_turn(command, user_id)

    def display_cards_for_player_in_pm(self, player_id, cards):
        """Displays the cards for the players in a private message

        Args:
            [player_id] (str) id of the player
            [cards] (str) the cards to display
        Returns:
        """
        print "display_cards_for_player_in_pm(self, player_id, cards) "
        print "  player_id: ", player_id
        print "  player: ", self.bot.user_ids_to_username[player_id]
        print "  cards: ", cards

        formatted_cards = helper_functions.interactiformat(cards)
        # the player has more than 5 cards, so we have to send them in separate messages
        self.bot.first_set = False
        if len(cards) > 5:
            print "  len(cards) > 5"
            five_card_set = {}
            for idx, card in enumerate(cards):
                if idx == 0: # add the first card
                    self.bot.first_set = True
                    print "  idx == 0"
                    print "  formatted_cards[idx] = ", formatted_cards[idx]
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) != 0: # add the next 4
                    print "  (idx % 5) != 0"
                    print "  formatted_cards[idx] = ", formatted_cards[idx]
                    five_card_set[idx] = formatted_cards[idx]
                elif (idx % 5) == 0: # we've hit the 5th card that sends a new message
                    print "  (idx % 5) == 0"
                    attachments = helper_functions.interactify(five_card_set,self.bot.first_set)
                    print "  *posting whole set of five"
                    slack.chat.post_message(
                        channel=player_id,
                        as_user=True,
                        attachments=attachments
                        )
                    self.bot.first_set = False
                    five_card_set.clear() # clear the set
                    five_card_set[idx] = formatted_cards[idx] # add the first card of the next set
                    print "  five_card_set (first card of next set): ", five_card_set
                if len(cards) == (idx + 1): # we've reached the last card so post the remaining cards to the user
                    print "  len(cards) == (idx + 1)"
                    attachments = helper_functions.interactify(five_card_set,self.bot.first_set)
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
            self.bot.first_set = True
            attachments = helper_functions.interactify(formatted_cards,self.bot.first_set)
            print "  *posting set of 0-5"
            slack.chat.post_message(
                channel=player_id,
                as_user=True,
                attachments=attachments
                )
