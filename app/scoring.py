from slackclient import SlackClient
import helper_functions
import game as DrumpfGame
import random
import models

import os
import sys

class Scoring():

    def __init__(self,bot,user_id):
        print "Initializing Scoring() class."
        self.bot = bot
        self.first_round = True
        self.pm_scoreboard_ts = ""
        self.slack_client = ""
        token = models.get_bot_access_token(user_id)
        # for token in tokens:
        try:
            print "  bot_access_token: ",token
            self.BOT_TOKEN = token
            self.slack_client = SlackClient(token)
            test_call = self.slack_client.api_call("users.list")
            if test_call.get('ok'):
                print "  Scoring() __init__ test_call is GOOD!"
        except:
            print "  exception on token retrieval attempt"
        else:
            print "  successful token retrieval"

    def build_scoreboard(self,msg):
        """
        Concatenates the incoming message to a continuous string of scoreboard data

        Args:
                [msg] (str) the message to be concatenated
        Returns:
        """
        self.bot.scoreboard += msg
        return

    def update_scoreboard(self, message, attachments=None):
        """
        Posts the updated scoreboard to the main channel

        Args:
                [msg] (str) the message to post
        """

        self.slack_client.api_call(
            "chat.update",
            channel=self.bot.main_channel_id,
            text=message,
            ts=self.bot.ts,
            as_user=True, attachments=attachments
        )

    def calculate_and_display_points_for_players(self):
        """
        Handles the logic for calculating players points
        """
        print "calculate_and_display_points_for_players(self) "
        msg = "*Round {} over!* _calculating points..._\n".format(self.bot.current_game.current_round)
        self.build_scoreboard(msg)
        self.bot.scoreboard = "*`Previous Round Recap`*\n" + self.bot.scoreboard
        self.update_scoreboard(self.bot.scoreboard)
        self.pm_users_scoreboard(self.bot.scoreboard)
        self.winning_scores = {}
        for idx, player_id in enumerate(self.bot.users_in_game):
            current_players_bid = self.bot.player_bids_for_current_round[player_id]
            points_off_from_bid = abs(current_players_bid - self.bot.player_points_for_round[player_id])
            if player_id in self.bot.shower_card_holder and player_id not in self.bot.zero_point_players:
                self.bot.game_scorecard[player_id] += 175
            elif player_id in self.bot.zero_point_players:
                self.bot.game_scorecard[player_id] += 0
            elif points_off_from_bid == 0:
                #The player got his/her bid correctly
                self.bot.game_scorecard[player_id] += (50 + 25 * current_players_bid)
            else:
                #player loses 25-points for every point above or below bid
                self.bot.game_scorecard[player_id] -= 25 * points_off_from_bid
            if self.bot.game_scorecard[player_id] >= self.bot.winning_points:
                self.winning_scores[player_id] = self.bot.game_scorecard[player_id]
        self.bot.scores += ">>>*Score Board*\n"
        print "  ",self.bot.scores
        for player_id in self.bot.users_in_game:
            if player_id in self.bot.shower_card_holder:
                msg = "><@{}>: *{} Points* _(Golden Shower card holder wins 175 points for the round)_\n".format(self.bot.user_ids_to_username[player_id], self.bot.game_scorecard[player_id])
                self.bot.scores += msg
            elif player_id in self.bot.zero_point_players:
                msg = "><@{}>: *{} Points* _(VM: The Blacks means the player neither loses nor gains points for the round)_\n".format(self.bot.user_ids_to_username[player_id], self.bot.game_scorecard[player_id])
                self.bot.scores += msg
            else:
                msg = "><@{}>: *{} Points*\n".format(self.bot.user_ids_to_username[player_id], self.bot.game_scorecard[player_id])
                self.bot.scores += msg

        self.update_scores(self.bot.scores)
        # self.pm_users_scoreboard(self.bot.scoreboard)
        self.pm_users_scores(self.bot.scores)

        self.bot.prepare_for_next_round()
        if self.bot.current_game.current_round == self.bot.current_game.final_round:
            self.present_winner_for_game(self.bot.user_ids_to_username[player_id],player_id)
        elif self.winning_scores:
            if len(self.winning_scores) > 1:
                self.winning_score = max(self.winning_scores.values())
                winner = self.winning_scores.keys()[self.winning_scores.values().index(self.winning_score)]
                self.present_winner_for_game(self.bot.user_ids_to_username[winner],winner)
            else:
                self.winning_score = self.winning_scores.values()[0]
                winner = self.winning_scores.keys()[self.winning_scores.values().index(self.winning_score)]
                self.present_winner_for_game(self.bot.user_ids_to_username[winner],winner)
        else:
            self.bot.current_game.play_round()

    def pm_users_scoreboard(self, board, attachments=None):
        """
        Private messages the relevant users the scoreboard

        Args:
                [board] the scoreboard
        """
        print "pm_users_scoreboard(self, board, attachments=None)"
        for player_id in self.bot.users_in_game:
            resp = self.slack_client.api_call(
                "chat.update",
                channel=player_id,
                text=board,
                ts=self.pm_scoreboard_ts
                as_user=True,
                attachments=attachments
            )

    def init_pm_scoreboard(self, board, attachments=None):
        """
        Initializes the scoreboard for players in pm

        Args:
                [board] the scoreboard
        """
        print "init_pm_scoreboard(self, board, attachments=None)"
        if self.first_round:
            for player_id in self.bot.users_in_game:
                resp = self.slack_client.api_call(
                    "chat.postMessage",
                    channel=player_id,
                    text=board,
                    as_user=True,
                    attachments=attachments
                )
                self.pm_scoreboard_ts = resp['ts']
                event = "pm_scoreboard"
                models.log_message_ts(self.pm_scoreboard_ts,player_id,event,self.bot.team_id)
        else:
            for player_id in self.bot.users_in_game:
                resp = self.slack_client.api_call(
                    "chat.update",
                    channel=player_id,
                    ts = self.pm_scoreboard_ts
                    text=board,
                    as_user=True,
                    attachments=attachments
                )
        self.first_round = False

    def pm_users_scores(self, scores, attachments=None):
        """
        Private messages the relevant users the scores

        Args:
                [scores] the players scores
        """
        print "pm_users_scores(self, scores, attachments=None)"
        for player_id in self.bot.users_in_game:
            resp_scores = self.slack_client.api_call(
                "chat.postMessage",
                channel=player_id,
                text=scores,
                as_user=True, attachments=attachments
            )

    def initialize_scores(self, attachments=None):
        """
        Initializes the score output (i.e. Player1 - 0, Player2 - 0) and displays to main channel
        """
        print "initialize_scores(self, attachments=None)"
        msg = ""
        msg += ">>>*Score Board*"

        for player_id in self.bot.users_in_game:
            msg += "\n><@{}>: *{} Points*".format(self.bot.user_ids_to_username[player_id], self.bot.game_scorecard[player_id])

        resp = self.slack_client.api_call(
            "chat.postMessage",
            channel=self.bot.main_channel_id,
            text=msg,
            as_user=True, attachments=attachments
        )
        self.bot.ts_scores = resp['ts']
        team_id = self.bot.team_id
        event = "scores"
        models.log_message_ts(self.bot.ts_scores,self.bot.main_channel_id,event,team_id)

    def update_scores(self, message, attachments=None):
        """
        Posts the updated scores to the main channel

        Args:
                [message] (str) the score data to send
        """
        print "update_scores(self, message, attachments=None)"
        self.slack_client.api_call(
            "chat.update",
            channel=self.bot.main_channel_id,
            text=message,
            ts=self.bot.ts_scores,
            as_user=True, attachments=attachments
        )

    def determine_winner_for_sub_round(self, card):
        """
        Handles all logic pertaining to determining a winner for a sub-round

        Args:
                [card] (str) the card to evaluate
        """
        print "determine_winner_for_sub_round(self, card) "
        self.bot.winning_sub_round_card = None
        num_cards_played = len(self.bot.cards_played_for_sub_round)

        card_value_sub_round = None
        card_suit_sub_round = None

        # reset after each sub-round
        self.bot.first_card_sub_round = 0

        if len(self.bot.cards_played_for_sub_round[0]) == 2:
            card_value_sub_round = str(self.bot.cards_played_for_sub_round[0][0])
            card_suit_sub_round = self.bot.cards_played_for_sub_round[0][1]
        else:
            card_value_sub_round = str(self.bot.cards_played_for_sub_round[0])
            card_suit_sub_round = None
        # everyone has played VM cards, first person to play one wins
        if  all(x[0:3]=="vm_" for x in self.bot.cards_played_for_sub_round):
            self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[0]
            self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[0]
            return
        # make sure the t_shower card holder gets set
        if "t_shower" in self.bot.cards_played_for_sub_round:
            t_shower_idx = self.bot.cards_played_for_sub_round.index("t_shower")
            self.bot.shower_card_holder.append(self.bot.player_turn_queue_reference[t_shower_idx])
        # make sure the vm_blacks card holder gets set
        if "vm_blacks" in self.bot.cards_played_for_sub_round:
            vm_blacks_idx = self.bot.cards_played_for_sub_round.index("vm_blacks")
            self.bot.zero_point_players.append(self.bot.player_turn_queue_reference[vm_blacks_idx])
        # Russian Blackmail card wins in every situation
        if "t_russian" in self.bot.cards_played_for_sub_round:
            t_russian_idx = self.bot.cards_played_for_sub_round.index("t_russian")
            self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[t_russian_idx]
            self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[t_russian_idx]
            return
        # everyone played Tremendous cards, no t_russian card, so first person to play wins
        if  all(x[0:2]=="t_" for x in self.bot.cards_played_for_sub_round):
            if "t_russian" not in self.bot.cards_played_for_sub_round:
                self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[0]
                self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[0]
                return
        else:
            #we have to iterate over the cards to determine the winner for the sub-round
            winning_card = None
            trump_suit = self.bot.current_game.current_round_trump_suit
            card_value = None
            card_suit = None
            visited = False # keeps track of the case of pussy/ivanka/nasty cards all being played same round
            for idx, card in enumerate(self.bot.cards_played_for_sub_round):
                if len(card) == 2:
                    card_value = str(card[0])
                    card_suit = card[1]
                else:
                    card_value = str(card)
                    card_suit = None
                current_player = self.bot.player_turn_queue_reference[idx]
                # handle Tremendous cards and Drumpf cards
                if card_value.startswith("t_") or card_value.startswith("d_"):
                    # comey card steals Clinton's Email Server card
                    if card_value.startswith("d_clinton"):
                        if "t_comey" in self.bot.cards_played_for_sub_round:
                            comey_card_idx = self.bot.cards_played_for_sub_round.index("t_comey")
                            if idx < comey_card_idx:
                                msg = "{} card steals {} card...\n".format(helper_functions.emojify_card(self.bot.cards_played_for_sub_round[comey_card_idx]),helper_functions.emojify_card(card_value))
                                self.build_scoreboard(msg)
                                self.update_scoreboard(self.bot.scoreboard)
                                self.pm_users_scoreboard(self.bot.scoreboard)
                                # for player_id in self.bot.users_in_game:
                                #     self.bot.private_message_user(player_id,msg)

                                self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[comey_card_idx]
                                self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[comey_card_idx]
                                return
                            else:
                                self.bot.winning_sub_round_card = card
                                self.bot.winner_for_sub_round = current_player
                                return
                        elif "t_nasty" in self.bot.cards_played_for_sub_round:
                            nasty_card_idx = self.bot.cards_played_for_sub_round.index("t_nasty")
                            if idx < nasty_card_idx:
                                msg = "{} card negates {} card...\n".format(helper_functions.emojify_card(self.bot.cards_played_for_sub_round[nasty_card_idx]),helper_functions.emojify_card(card_value))
                                self.build_scoreboard(msg)
                                self.update_scoreboard(self.bot.scoreboard)
                                self.pm_users_scoreboard(self.bot.scoreboard)
                                # for player_id in self.bot.users_in_game:
                                #     self.bot.private_message_user(player_id,msg)

                                self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[nasty_card_idx]
                                self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[nasty_card_idx]
                                return
                            else:
                                print "  {} card wins".format(card)
                                self.bot.winning_sub_round_card = card
                                self.bot.winner_for_sub_round = current_player
                                return
                        else:
                            self.bot.winning_sub_round_card = card
                            self.bot.winner_for_sub_round = current_player
                            return

                    # The Wall card can be usurped by the Bad Hombres
                    elif card_value.startswith("d_wall"):
                        print "  handling {} card...".format(card_value)
                        if "vm_hombres" in self.bot.cards_played_for_sub_round:
                            hombres_card_idx = self.bot.cards_played_for_sub_round.index("vm_hombres")
                            if idx < hombres_card_idx:

                                msg = "{} card steals {}\n".format(helper_functions.emojify_card(self.bot.cards_played_for_sub_round[hombres_card_idx]),helper_functions.emojify_card(card_value))
                                self.build_scoreboard(msg)
                                self.update_scoreboard(self.bot.scoreboard)
                                self.pm_users_scoreboard(self.bot.scoreboard)
                                # for player_id in self.bot.users_in_game:
                                #     self.bot.private_message_user(player_id,msg)

                                self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[hombres_card_idx]
                                self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[hombres_card_idx]
                                return
                            else:
                                self.bot.winning_sub_round_card = card
                                self.bot.winner_for_sub_round = current_player
                                return
                        elif "t_nasty" in self.bot.cards_played_for_sub_round:
                            nasty_card_idx = self.bot.cards_played_for_sub_round.index("t_nasty")
                            if idx < nasty_card_idx:
                                msg = "{} card negates {} card...\n".format(helper_functions.emojify_card(self.bot.cards_played_for_sub_round[nasty_card_idx]),helper_functions.emojify_card(card_value))

                                self.build_scoreboard(msg)
                                self.update_scoreboard(self.bot.scoreboard)
                                self.pm_users_scoreboard(self.bot.scoreboard)
                                # for player_id in self.bot.users_in_game:
                                #     self.bot.private_message_user(player_id,msg)
                                self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[nasty_card_idx]
                                self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[nasty_card_idx]
                                return
                            else:
                                self.bot.winning_sub_round_card = card
                                self.bot.winner_for_sub_round = current_player
                                return
                        else:
                            self.bot.winning_sub_round_card = card
                            self.bot.winner_for_sub_round = current_player
                            return
                    # the regular old Drumpf cards
                    elif card_value.startswith("d_pussy") or card_value.startswith("d_ivanka"):
                        # the non-negated Drumpf wins
                        if visited:
                            self.bot.winning_sub_round_card = card
                            self.bot.winner_for_sub_round = current_player
                            return
                        else:
                            if "t_nasty" in self.bot.cards_played_for_sub_round:
                                nasty_card_idx = self.bot.cards_played_for_sub_round.index("t_nasty")
                                if idx < nasty_card_idx:
                                    visited = True
                                    msg = "*{} card negates {} card...\n".format(helper_functions.emojify_card(self.bot.cards_played_for_sub_round[nasty_card_idx]),helper_functions.emojify_card(card_value))

                                    self.build_scoreboard(msg)
                                    self.update_scoreboard(self.bot.scoreboard)
                                    self.pm_users_scoreboard(self.bot.scoreboard)
                                    # for player_id in self.bot.users_in_game:
                                    #     self.bot.private_message_user(player_id,msg)
                                    self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[nasty_card_idx]
                                    self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[nasty_card_idx]
                                    return
                                else:
                                    self.bot.winning_sub_round_card = card
                                    self.bot.winner_for_sub_round = current_player
                                    return
                            else:
                                self.bot.winning_sub_round_card = card
                                self.bot.winner_for_sub_round = current_player
                                return

                    elif card_value.startswith("t_nasty") or card_value.startswith("t_comey"):
                        print "  *this card is a pass card since no other trumping or stealing cards have been played"
                        continue

                elif card_value[0:3] == "vm_":
                    if "muslims" in card_value or "thieves" in card_value or "hombres" in card_value:
                        # to get to this point, t_comey or t_nasty or t_shower must be the only other card and played first, so the VM card wins
                        if self.bot.winning_sub_round_card == None:
                            print "  *No self.bot.winning_sub_round_card set so the remaining VM card must be the winner"
                            self.bot.winning_sub_round_card = card
                            self.bot.winner_for_sub_round = current_player
                        continue

                    if "blacks" in card_value:
                        # self.bot.zero_point_players.append(current_player)

                        # to get to this point, t_comey or t_nasty or t_shower must be the only other card and played first, so no winner is present.
                        if self.bot.winning_sub_round_card == None:
                            for t_card in self.bot.t_cards:
                                if t_card == "t_russian":
                                    print "    *passing on t_russian card"
                                    pass
                                elif t_card in self.bot.cards_played_for_sub_round:
                                    t_idx = self.bot.cards_played_for_sub_round.index(t_card)
                                    if t_idx < idx:
                                        print "  a t_card has been played before the vm_blacks card, so it wins"
                                        self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[t_idx]
                                        self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[t_idx]
                                        return
                                    else:
                                        print "  a t_card has been played after the vm_blacks card, so it loses"
                                        self.bot.winning_sub_round_card = self.bot.cards_played_for_sub_round[idx]
                                        self.bot.winner_for_sub_round = self.bot.player_turn_queue_reference[idx]
                                        return
                                else:
                                    print "***SOMEHOW GOT HERE???"
                        continue
                    continue
                # the card is a trump suit card
                elif card_suit == trump_suit:
                    if self.bot.winning_sub_round_card == None:
                        self.bot.winning_sub_round_card = card
                        self.bot.winner_for_sub_round = current_player
                    elif self.bot.winning_sub_round_card[1] == trump_suit:
                        if DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.bot.winning_sub_round_card):
                            print "  trump suit played second beats previous trump suit"
                            #trump suit played beats previous trump suit
                            self.bot.winning_sub_round_card = card
                            self.bot.winner_for_sub_round = current_player
                    else:
                        print "  *Got to this else statement!!!"
                        self.bot.winning_sub_round_card = card
                        self.bot.winner_for_sub_round = current_player
                elif card_suit == self.bot.leading_suit:
                    if self.bot.winning_sub_round_card == None:
                        print "  no self.bot.winning_sub_round_card"
                        self.bot.winning_sub_round_card = card
                        self.bot.winner_for_sub_round = current_player
                    elif DrumpfGame.drumpf_deck.index(card) > DrumpfGame.drumpf_deck.index(self.bot.winning_sub_round_card):
                        print "  the card index of {} is greater than the index of the winning sub-round card ({})".format(card,self.bot.winning_sub_round_card)
                        self.bot.winning_sub_round_card = card
                        self.bot.winner_for_sub_round = current_player
                elif self.bot.winning_sub_round_card == None:
                    print "  *The remaining card must be the winner"
                    self.bot.winning_sub_round_card = card
                    self.bot.winner_for_sub_round = current_player
                else:
                    print "  ***This card gets passed by because it does not win***"
                    print "    {} card passed by".format(card)
                    print "    player {} card has been passed".format(current_player)

    def present_winner_for_game(self,winner,pid):
        """
        Presents a winner for the game, posting to the main Slack channel

        Args:
                [winner] (str) the game winner's name
                [pid] (str) the id of the winner
        """
        print "present_winner_for_game(self) "
        score = self.bot.game_scorecard[pid]
        response = "And our winner for the game is *{}*!\n:cake: :birthday: :fireworks: *Score: `{}`* :fireworks: :birthday: :cake:\n".format(winner,score)

        image_urls = ["https://media.giphy.com/media/ytwDCq9aT3cgEyyYVO/giphy.gif",
        "https://media.giphy.com/media/YTbZzCkRQCEJa/giphy.gif",
        "https://media.giphy.com/media/jMBmFMAwbA3mg/giphy.gif",
        "https://media.giphy.com/media/l0MYxef0mpdcnQnvi/source.gif",
        "https://media.giphy.com/media/3o7TKtsBMu4xzIV808/giphy.gif",
        "https://media.giphy.com/media/l3q2Z6S6n38zjPswo/giphy.gif",
        "https://media.giphy.com/media/kmqCVSHi5phMk/giphy.gif",
        "https://media.giphy.com/media/9X5zV9eHAqAus/giphy.gif",
        "https://media.giphy.com/media/Xv0Y0A2GsrZ3G/giphy.gif"]
        random.shuffle(image_urls)
        image_url = image_urls[0]
        attachments = [
            {
                "title": "Celebrate good times!",
                "image_url": image_url
            }]

        self.slack_client.api_call(
            "chat.update",
            channel=self.bot.main_channel_id,
            text=response,
            ts=self.bot.ts,
            attachments = attachments,
            as_user=True
        )
        for player in self.bot.current_game.players:
            self.bot.private_message_user(player.id,response,attachments)
        # TODO: Prompt user if they wish to clear the main channel or not (also use this to restart the program)
        # self.bot.restart_program()
