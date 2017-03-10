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
import models

from app import app

@app.task
def launch_bot(user_id,channel,ts,team_id):
    '''
    Instantiates the necessary objects to play a game

    Args:
            [user_id] (str) The id of the user from which the command was sent
            [channel] (str) The channel the command was posted in
            [ts] (str) The timestamp of the command

    '''
    print "launch_bot(user_id,channel)"
    app.control.purge()
    bot = DrumpfBot()
    bot.initialize(user_id, channel)
    score = Scoring(bot, user_id)
    bid = Bid(bot,score)
    trump = TrumpSuit(bot,score,bid)
    round_ = Round(bot,score,trump)
    bot.main(score, bid, trump, round_, team_id)

@app.task
def log_message_ts(ts,channel,event,team_id):
    '''
    Logs an incoming message timestamp in the database for the purpose of eventually cleaning up the main message channel

    Args:
            [ts] (str) The timestamp of the message
            [channel] (str) The channel the message was posted in
            [event] (str) The event type that the timestamp correlates to
            [team_id] (str) The id of the team in which the message was sent
    '''
    print "log_message_ts(ts,channel)"
    values = {"event": event, "channel": channel, "ts": ts, "team_id": team_id}
    df = pd.DataFrame(values, index=[0])
    engine = models.get_engine()
    models.send_to_db(df,engine,'messages')
