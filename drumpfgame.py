import random

drumpf_deck = ["vm_blacks", "vm_hombres", "vm_muslims", "vm_thieves"]
suits = ["diamonds", "clubs", "hearts", "spades"]
values = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K"]
# # values = [2, 3, "J", "Q", "K"]
for suit in suits:
    for value in values:
        drumpf_deck.append([value, suit])
drumpf_deck = drumpf_deck + ["d_pussy", "d_wall", "d_clinton", "d_ivanka"]
# drumpf_deck = ["d_pussy", "d_wall", "d_clinton", "d_ivanka"]
drumpf_deck = drumpf_deck + ["t_russian", "t_nasty","t_shower","t_comey"]

def rotate_list(l, n):
    return l[-n:] + l[:-n]

class Player:
    def __init__(self, id):
        self.points = 0
        self.id = id
        self.cards_in_hand = []

    def receive_card(self, card):
        self.cards_in_hand.append(card)

class Deck: #preshuffled deck
    def __init__(self):
        self.cards = drumpf_deck[:]
        random.shuffle(self.cards)

    def deal_card(self):
        return self.cards.pop()

class Game:
    def __init__(self, players, bot):
        #[Player1, Player2, Player3, ...etc]
        self.players = deque(players)
        self.final_round = 60/len(players) #i.e. 12 rounds for 5 players
        self.current_round = 1
        self.current_round_trump_suit = None
        self.bot = bot
        self.bot.current_game = self

    # 1) creates a new shuffled deck
    # 2) deals cards to the players depending on the round #
    # 3) determines trump suit (or asks dealer for it)
    # 4) gets bids from players
    # 5) plays mini-rounds & allocates points until round is over
    def play_round(self):
        print "play_round(self) "
        shuffled_deck = Deck()
        for _ in range(0, self.current_round):
            self.deal_single_card_to_each_player(shuffled_deck)

        #determine trump suit according to default rules
        if len(shuffled_deck.cards) > 0:
            print "  len(shuffled_deck.cards) > 0"
            trump_card = shuffled_deck.cards.pop()
            trump_value = None
            trump_suit = None
            if len(trump_card) == 2: # regular card
                print "  *dealing with a regular card"

                trump_value = str(trump_card[0])
                print "  Trump Value: ", trump_value

                trump_suit = trump_card[1]
                print "  Trump Suit: ", trump_suit

                self.bot.current_game.current_round_trump_suit = trump_suit
                print "  self.bot.current_game.current_round_trump_suit set to: {}".format(self.bot.current_game.current_round_trump_suit)

            else: # special card
                trump_value = trump_card
                print "  Trump Value: ", trump_value
                trump_suit = None
            # is a tremendous, drumpf
            if trump_value[0:2] == "d_" or trump_value[0:2] == "t_":
                print "  *dealing with a d_ or t_ card"
                self.bot.drumpfmendous_card_first = True
                self.bot.prompt_dealer_for_trump_suit(self.players[0].id)

            # or visible minority card
            elif trump_value[0:3] == "vm_":
                print "  *dealing with a vm_ card"
                trump_suit = None

        elif len(shuffled_deck.cards) == 0:
            print "  len(shuffled_deck.cards) == 0"
            self.bot.prompt_dealer_for_trump_suit(self.players[0].id)
        for player in self.players:
            self.bot.display_cards_for_player_in_pm(player.id,
                                                    player.cards_in_hand)
        self.bot.get_bids_from_players(self.current_round, self.players)
        self.bot.current_game.current_round_trump_suit = trump_suit
        self.bot.announce_trump_card(trump_card)
        self.players.rotate(1)
        #dealer is always index 0 of players and we will rotate the array end of each turn

    def deal_single_card_to_each_player(self, deck):
        print "deal_single_card_to_each_player(self, deck) "
        for player in self.players:
            player.receive_card(deck.deal_card())
