import helper_functions
import copy

class Round():

    def __init__(self,bot,score,trump):
        self.bot = bot
        self.score = score
        self.trump = trump

    def get_card_being_played(self, user_id, index): # -> ex. ['K', 'spades']
        """Takes the users id and index of the card being played and returns the actual card as a string

        Args:
            [user_id] (str) the player id of the user
            [index] (int) the id of the user sending the index of the care being played relative to the players hand
        Returns:
            [user_object.cards_in_hand[index]] (str) the string value of the card index
            [None] (NoneType) nothing in the case of the index being out of range of the cards in the players hand
        """
        print "get_card_being_played(self, user_id, index) "
        print "  user_id: ",user_id
        print "  player: ", self.bot.user_ids_to_username[user_id]
        print "  index: ",index

        for user_object in self.bot.current_game.players:
            if user_object.id == user_id:
                print "  cards in hand: {}".format(user_object.cards_in_hand)
                if index > len(user_object.cards_in_hand):
                    return None
                else:
                    return user_object.cards_in_hand[index]

    def handle_player_turn(self, command, user_id):
        """Verifies that the user input is valid and from the correct player, and then initiates an action based on that logic

        Args:
            [command] (str) the integer command of the card to be played
            [user_id] (str) the player id of the user
        Returns:
        """
        print "handle_player_turn(self, command, user_id) "
        print "  command: ", command
        print "  user_id: ", user_id
        print "  player: ", self.bot.user_ids_to_username[user_id]

        response = ""
        current_username = self.bot.user_ids_to_username[self.bot.player_turn_queue[0]]
        print("  User sending message: {}".format(self.bot.user_ids_to_username[user_id]))
        #waiting for first player after dealer to play a card
        if user_id != self.bot.player_turn_queue[0]:
            response = "Waiting for <@{}> to play a card.".format(current_username)
        elif user_id == self.bot.player_turn_queue[0]:
            print('  Received input from expected player: {}'.format(current_username))

            print "  self.bot.current_game.current_round: {}".format(self.bot.current_game.current_round)

            print "  self.bot.sub_rounds_played + 1 : {}".format(self.bot.sub_rounds_played + 1)

            allowable_index = int(self.bot.current_game.current_round) - (int(self.bot.sub_rounds_played) + 1)
            print "  set allowable_index: {}".format(allowable_index)

            # the command must be between 0 and the largest index of the card in the players hand
            if int(command) >= 0 and int(command) <=  allowable_index:
                print("  Selected a valid card index")
                card_being_played = self.get_card_being_played(user_id, int(command))

                if card_being_played == None:
                    self.bot.private_message_user(user_id, "That's not a valid card index")
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

                self.bot.first_card_sub_round += 1


                #otherwise valid card played
                if self.bot.leading_suit != None:
                    print "  self.bot.leading_suit != None"
                    print("  Sub-round trump suit: {}".format(self.bot.leading_suit))
                    #a drumpf or a visible minority card or a tremendous card is always a valid play
                    if card_value.startswith("d_") or card_value.startswith("vm_") or card_value.startswith("t_"):
                        self.handle_valid_card_played(card_being_played)
                    elif self.bot.leading_suit == "Any":
                        #a drumpf was played as the first card
                        #players are free to play whatever they want
                        self.handle_valid_card_played(card_being_played)
                    elif card_suit == self.bot.leading_suit:
                        #card played same suit as sub_round_suit
                        self.handle_valid_card_played(card_being_played)
                    elif self.trump.player_hand_contains_suit(user_id, self.bot.leading_suit) == False:
                        #any card is valid, because player doesn't have the initial suit
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.bot.private_message_user(user_id, "Sorry, you can't play that card")
                elif self.bot.leading_suit == None:
                    print("  There is no sub-round trump suit set yet....")
                    if card_value.startswith("d_") or card_value.startswith("t_"):
                        print("  {} played a Drumpf or Tremendous  Card first".format(current_username))
                        # nasty card played first gets to set suit
                        if self.bot.first_card_sub_round == 1:
                            print "  self.bot.first_card_sub_round == 1"
                            if "t_nasty" in card_value:
                                print "  player holds t_nasty and so gets to choose trump suit"
                                self.trump.prompt_dealer_for_trump_suit(user_id)
                            else:
                                self.bot.leading_suit = "Any"
                                self.handle_valid_card_played(card_being_played)
                        else:
                            self.bot.leading_suit = "Any"
                            self.handle_valid_card_played(card_being_played)
                    elif card_value.startswith("vm_"):
                        print("  {} played a Visible Minority Card".format(current_username))
                        #the sub round suit stays None until a player plays a suited card
                        self.handle_valid_card_played(card_being_played)
                    else:
                        self.bot.leading_suit = card_suit
                        print("  Sub-round trump suit set to {}".format(card_suit))
                        self.handle_valid_card_played(card_being_played)
            else:
                response = "That wasn't a valid card index."
        self.bot.private_message_user(user_id, response)

    def handle_valid_card_played(self, card):
        """Takes a card which has been determined to be valid and invokes other functions to decide the outcome of the card, the result of which is displayed to the user

        Args:
            [card] (str) the card to be evaluated
        Returns:
        """
        print "handle_valid_card_played(self, card) "
        print "  card: ",card

        player_who_played_card = self.bot.user_ids_to_username[self.bot.player_turn_queue[0]]
        self.remove_card_from_players_hand(self.bot.player_turn_queue[0], card)

        card_emoji = helper_functions.emojify_card(card)
        msg = "><@{}> played {}\n".format(player_who_played_card, card_emoji)
        print " ",msg
        self.score.build_scoreboard(msg)
        self.score.update_scoreboard(self.bot.scoreboard)
        self.score.pm_users_scoreboard(self.bot.scoreboard)
        # for player_id in self.bot.users_in_game:
        #     self.bot.private_message_user(player_id,msg)

        self.bot.cards_played_for_sub_round.append(card)
        print("  Cards played for sub-round: {}".format(self.bot.cards_played_for_sub_round))

        print "    self.bot.player_turn_queue before popleft(): {}".format(self.bot.player_turn_queue)
        self.bot.player_turn_queue.popleft()
        print "    self.bot.player_turn_queue after popleft(): {}".format(self.bot.player_turn_queue)

        print("  Player turn queue: {}".format(self.bot.player_turn_queue))
        if len(self.bot.player_turn_queue) == 0:
            self.bot.sub_rounds_played += 1

            print("  >Everyone played, time to determine winner for sub-round")
            self.score.determine_winner_for_sub_round(card)

            self.bot.player_points_for_round[self.bot.winner_for_sub_round] += 1

            msg = ">*<@{}> won this sub-round with a {}*\n\n".format(self.bot.winner_for_sub_round,helper_functions.emojify_card(self.bot.winning_sub_round_card))
            print " ",msg
            self.score.build_scoreboard(msg)
            self.score.update_scoreboard(self.bot.scoreboard)
            # for player_id in self.bot.users_in_game:
            #     self.bot.private_message_user(player_id,msg)

            #reset all sub-round variables
            self.bot.leading_suit = None
            self.bot.cards_played_for_sub_round = []

            if self.bot.sub_rounds_played == self.bot.current_game.current_round:
                print "  >Sub-round is over, time to tally points and display them"
                print "    player_turn_queue: %s" % self.bot.player_turn_queue
                print "    player_bid_queue: %s" % self.bot.player_bid_queue
                print "    self.bot.users_in_game: %s" % self.bot.users_in_game
                print "    self.bot.player_bids_for_current_round: %s" % self.bot.player_bids_for_current_round

                self.score.calculate_and_display_points_for_players()
                self.bot.winner_for_sub_round = None
            elif self.bot.sub_rounds_played < self.bot.current_game.current_round:
                msg = ">_Sub-Round {}_\n".format(self.bot.sub_rounds_played + 1)
                self.score.build_scoreboard(msg)
                self.score.update_scoreboard(self.bot.scoreboard)
                self.score.pm_users_scoreboard(self.bot.scoreboard)
                # for player_id in self.bot.users_in_game:
                #     self.bot.private_message_user(player_id,msg)

                #initialize another turn queue cause there are more cards to play
                self.bot.player_turn_queue = copy.copy(self.bot.users_in_game)

                print "    player_turn_queue: %s" % self.bot.player_turn_queue
                print "    player_bid_queue: %s" % self.bot.player_bid_queue
                print "    self.bot.users_in_game: %s" % self.bot.users_in_game
                print "    self.bot.player_bids_for_current_round: %s" % self.bot.player_bids_for_current_round

                while self.bot.player_turn_queue[0] != self.bot.winner_for_sub_round:
                    print("  *Rotating player turn queue")
                    #rotate player_turn_queue until the first player is the one who won
                    self.bot.player_turn_queue.rotate(1)
                print "    player_turn_queue: %s" % self.bot.player_turn_queue
                print "    player_bid_queue: %s" % self.bot.player_bid_queue
                print "    self.bot.users_in_game: %s" % self.bot.users_in_game
                print "    self.bot.player_bids_for_current_round: %s" % self.bot.player_bids_for_current_round

                self.bot.player_turn_queue_reference = copy.copy(self.bot.player_turn_queue)
                self.bot.winner_for_sub_round = None
                for player in self.bot.current_game.players:
                    if player.id == self.bot.player_turn_queue[0]:
                        msg = "Play a card."
                        self.bot.display_cards_for_player_in_pm(self.bot.player_turn_queue[0],player.cards_in_hand,msg)
                        # self.bot.private_message_user(self.bot.player_turn_queue[0], "Play a card.")
        else:
            for player in self.bot.current_game.players:
                if player.id == self.bot.player_turn_queue[0]:
                    msg = "Play a card."
                    self.bot.display_cards_for_player_in_pm(self.bot.player_turn_queue[0],player.cards_in_hand,msg)
                    # self.bot.private_message_user(self.bot.player_turn_queue[0], "Play a card.")

    def remove_card_from_players_hand(self, current_player_id, card_to_remove):
        """Removes a card from the players hand

        Args:
            [current_player_id] (str) id of the player
            [card_to_remove] (str) the card to remove
        Returns:
        """
        print "remove_card_from_players_hand(self, current_player_id, card_to_remove) "
        print "  current_player_id: ",current_player_id
        print "  player: ", self.bot.user_ids_to_username[current_player_id]
        print "  card_to_remove: ",card_to_remove

        idx_of_card_to_remove = None
        for player in self.bot.current_game.players:
            if player.id == current_player_id:
                #we found the player, now remove the appropriate card from his/her hand
                for idx, card in enumerate(player.cards_in_hand):
                    if card == card_to_remove:
                        idx_of_card_to_remove = idx
                player.cards_in_hand.pop(idx_of_card_to_remove)
