import os

def format_cards_to_emojis(cards):
    print "format_cards_to_emojis(cards) "
    print "  cards: ",cards
    formatted_cards = []
    for idx, card in enumerate(cards):
        if len(card) == 2:
            formatted_cards.append("`{}`[{}:{}:]  ".format(idx, card[0], card[1]))
        else:
            formatted_cards.append("`{}`:{}:  ".format(idx, card))
    return "".join(formatted_cards)

def emojify_card(card):
    if not card:
        return ":{}:".format("")
    print "emojify_card(card) "
    print " card: ",card

    if len(card) == 2:
        return "[{}:{}:]".format(card[0], card[1])
    else:
        return ":{}:".format(card)

def interactiformat(cards):
    print "interactiformat(cards)"
    formatted_cards = {}
    for idx, card in enumerate(cards):
        if len(card) == 2:
            formatted_cards[idx] = "{}:{}:".format(card[0], card[1])
        else:
            formatted_cards[idx] = ":{}:".format(card)
    return formatted_cards

def interactify(cards,first_set):
    print "interactify(cards)"
    actions = []
    action = {}
    for key, value in cards.iteritems():
        action = {"name":value,"text":value,"type":"button","value":key}
        actions.append(action)
    values = "".join([x["text"] for x in actions])
    print "  values: ",values
    if first_set:
        attachments =[{"title":"Your cards good sir/mam:", "fallback":values, "callback_id":"interactify", "attachment_type":"default", "actions":actions}]
        print "  attachments: ",attachments
    else:
        attachments =[{"title":"", "fallback":values, "callback_id":"interactify", "attachment_type":"default", "actions":actions}]
        print "  attachments: ",attachments
    return attachments

def buttonify_bids(bid_set,first_set):
    print "buttonify_bids(bid_set)"
    actions = []
    action = {}
    for bid in bid_set:
        action = {"name":str(bid),"text":str(bid),"type":"button","value":int(bid)}
        actions.append(action)
    if first_set:
        attachments =[{"title":"What's your bid for the round?", "fallback":"Place a bid.", "callback_id":"buttonify_bids", "attachment_type":"default", "actions":actions}]
        print "  attachments: ",attachments
    else:
        attachments =[{"title":"", "fallback":"Place a bid.", "callback_id":"buttonify_bids", "attachment_type":"default", "actions":actions}]
        print "  attachments: ",attachments

    return attachments

def get_slack_client():
    token = os.environ.get('SLACK_BOT_TOKEN')
    return token