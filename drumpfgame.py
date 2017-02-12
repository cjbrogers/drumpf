import random
import drumpfbot as DrumpfBot

drumpf_deck = ["VM: blacks", "VM: hombres", "VM: muslims", "VM: thieves"]
suits = ["diamonds", "clubs", "hearts", "spades"]
values = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K"]
for suit in suits:
    for value in values:
        drumpf_deck.append([value, suit])
drumpf_deck = drumpf_deck + ["D: pussy", "D: wall", "D: clinton", "D: ivanka"]
drumpf_deck = drumpf_deck + ["T: russian", "T: nasty","T: shower","T: comey"]

drumpf_deck_special = ["blacks", "hombres", "muslims", "thieves"]
drumpf_deck_special = drumpf_deck_special + ["pussy", "wall", "clinton", "ivanka"]
drumpf_deck_special = drumpf_deck_special + ["russian", "nasty", "shower",
                                            "comey"]

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
        self.players = players
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
        print "==========================FUNCTION CALL=============================="
        print "\n__________________________ play_round(self) __________________________"
        shuffled_deck = Deck()
        for _ in range(0, self.current_round):
            self.deal_single_card_to_each_player(shuffled_deck)

        #determine trump suit according to default rules
        if len(shuffled_deck.cards) > 0:
            trump_card = shuffled_deck.cards.pop()
            trump_value = None
            trump_suit = None
            if len(trump_card) == 2: # regular card
                trump_value = str(trump_card[0])
                print "Trump Value: ", trump_value
                trump_suit = trump_card[1]
                print "Trump Suit: ", trump_suit
            else: # special card
                trump_value = trump_card
                print "Trump Card: ", trump_value
                trump_suit = None
            if trump_value.startswith("D:") or trump_value.startswith("T:") or trump_value.startswith("VM:"):
                #is a tremendous, drumpf or visible minority card
                if trump_value.startswith("D:") or trump_value.startswith("T:"):
                    self.bot.prompt_dealer_for_trump_suit(self.players[0].id)
                    self.bot.player_trump_card_queue.append(self.players[0].id)
                elif trump_value.startswith("VM:"):
                    trump_suit = None
            # elif len(trump_value) == 2: #regular card
            #     trump_suit = trump_suit
        elif len(shuffled_deck.cards) == 0:
            self.bot.prompt_dealer_for_trump_suit(self.players.first.id)
        for player in self.players:
            self.bot.display_cards_for_player_in_pm(player.id, player.cards_in_hand)
        self.bot.get_bids_from_players(self.current_round, self.players)
        self.bot.announce_trump_card(trump_card)
        #dealer is always index 0 of players and we will rotate the array end of each turn

    def deal_single_card_to_each_player(self, deck):
        print "==========================FUNCTION CALL=============================="
        print "\n__________________________ deal_single_card_to_each_player(self, deck) __________________________"
        for player in self.players:
            player.receive_card(deck.deal_card())
