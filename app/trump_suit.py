from slacker import Slacker
import helper_functions


# slack = Slacker(helper_functions.get_slack_client())
SUITS = ["diamonds", "clubs", "hearts", "spades"]

class TrumpSuit():

    def __init__(self,bot,score,bid):
        self.bot = bot
        self.slack = self.bot.slack
        self.score = score
        self.bid = bid

    def handle_trump_suit_selection(self,command,user_id):
        """Takes incoming command along with the user id and validates/sets trump suit

        Args:
            [command] (str) the integer command of the card suit index to be set as trump suit
            [user_id] (str) the id of the user sending the message
        Returns:
        """
        print "handle_trump_suit_selection(command, user_id) "
        print "  command: ",command
        print "  user_id: ",user_id
        print "  player: ", self.bot.user_ids_to_username[user_id]

        response = ""
        current_username = self.bot.user_ids_to_username[self.bot.player_trump_card_queue[0]]
        #we're waiting for a user to select a trump card
        if user_id != self.bot.player_trump_card_queue[0]:
            response = "Waiting for <@{}> to select a trump suit".format(current_username)
        elif user_id == self.bot.player_trump_card_queue[0]:
            #validate that the dealer picked a valid trump suit
            if (0 <= int(command) <= 3):
                self.bot.current_game.current_round_trump_suit = SUITS[int(command)]
                msg = "<@{}> chose :{}: for the trump suit.\n".format(current_username, SUITS[int(command)])
                self.score.build_scoreboard(msg)
                self.score.update_scoreboard(self.bot.scoreboard)
                self.score.pm_users_scoreboard(self.bot.scoreboard)

                # for player_id in self.bot.users_in_game:
                #     self.bot.private_message_user(player_id,msg)

                self.bot.player_trump_card_queue.pop()

                # for player in self.bot.player_turn_queue_reference:
                #     self.bot.private_message_user(player, response)

                if len(self.bot.player_bid_queue):
                    self.bid.present_bid_buttons(self.bot.player_bid_queue[0])
                else:
                    msg = "Play a card."
                    for player in self.bot.current_game.players:
                        if player.id == self.bot.player_turn_queue[0]:
                            self.bot.display_cards_for_player_in_pm(self.bot.player_turn_queue[0],player.cards_in_hand,msg)
                            # self.bot.private_message_user(self.bot.player_turn_queue[0], "Play a card.")
                return
            else:
                print "  That wasn't a valid index for a trump suit."
                response = "That wasn't a valid index for a trump suit."
        else:
            print "Whoops! Something went wrong."

        self.bot.private_message_user(user_id, response)

    def prompt_dealer_for_trump_suit(self, player_id):
        """Asks the dealer to choose trump suit (in a private message channel) - this presents buttons to the user as Slack message attachments

        Args:
            [player_id] (str) id of the player
        Returns:
        """
        print "prompt_dealer_for_trump_suit(self, player_id) "
        print "  player_id: ", player_id
        print "  player: ", self.bot.user_ids_to_username[player_id]
        self.bot.dealer_prompted_for_trump_suit = True

        self.bot.player_trump_card_queue.append(player_id)

        attachments =[{"title":"Please select index for trump suit:", "fallback":"Your interface does not support interactive messages.", "callback_id":"prompt_trump_suit", "attachment_type":"default", "actions":[{"name":"diamonds","text":":diamonds:","type":"button","value":"0"},
        {"name":"clubs","text":":clubs:","type":"button","value":"1"},
        {"name":"hearts","text":":hearts:","type":"button","value":"2"},
        {"name":"spades","text":":spades:","type":"button","value":"3"}]}]
        self.slack.chat.post_message(
            channel=player_id,
            as_user=True,
            attachments=attachments
            )

    def announce_trump_card(self, trump_card):
        """Announces the trump card to the main game channel and each user privately

        Args:
            [trump_card] (str) the trump card to announce
        Returns:
        """
        print "announce_trump_card(self, trump_card) "
        print "  trump_card: ",trump_card

        msg = "*Round {}* \n The trump card is: {} \n>_Sub-Round {}_\n".format(
            self.bot.current_game.current_round,
            helper_functions.emojify_card(trump_card),(self.bot.sub_rounds_played + 1))
        self.score.build_scoreboard(msg)
        self.score.update_scoreboard(self.bot.scoreboard)
        # self.score.pm_users_scoreboard(self.bot.scoreboard)
        self.score.init_pm_scoreboard(self.bot.scoreboard)

    def player_hand_contains_suit(self, user_id, suit):
        """Determines if the player has the leading suit in hand or not

        Args:
            [user_id] (str) the player id of the user
            [suit] (str) the leading suit to check for in the players hand
        Returns:
            [True] (bool) if the players hand contains the leading suit for the sub-round
            [False] (bool) if the players hand does not contain the leading suit for the sub-round
        """
        print "player_hand_contains_suit(self, user_id, suit) "
        print "  Checking if player hand contains expected suit:  {}".format(self.bot.leading_suit)
        for user_object in self.bot.current_game.players:
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
