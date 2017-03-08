import bot
from bot import DrumpfBot
import scoring
from scoring import Scoring
import bidding
from bidding import Bid
import round
from round import Round
import trump_suit
from trump_suit import TrumpSuit

from app import app

@app.task
def launch_bot(user_id,channel):
    print "launch_bot(user_id,channel)"
    bot = DrumpfBot()
    bot.initialize(user_id, channel)
    score = Scoring(bot, user_id)
    bid = Bid(bot,score)
    trump = TrumpSuit(bot,score,bid)
    round_ = Round(bot,score,trump)
    bot.main(score, bid, trump, round_)

@app.task
def add(x, y):
    return x + y
