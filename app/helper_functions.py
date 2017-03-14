import os
import models


def emojify_card(card):
    if not card:
        return ":{}:".format("")
    print "emojify_card(card) "
    print " card: ", card

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


def interactify(cards, first_set, current_round, msg="Your cards good sir/mam:"):
    print "interactify(cards)"
    actions = []
    action = {}
    for key, value in cards.iteritems():
        action = {
            "name": "play_card_{}".format(current_round),
                    "text": value,
                    "type": "button",
                    "value": key
        }
        actions.append(action)
    values = "".join([x["text"] for x in actions])
    print "  values: ", values

    color = ""
    if msg == "Play a card.":
        color = "#4CAF50"
    else:
        color = "#9E9E9E"
    attachments = [
        {
            "title": msg,
            "fallback": values,
            "color": color,
            "callback_id": "interactify",
            "attachment_type": "default",
            "actions": actions
        }]
    return attachments


def buttonify_bids(bid_set, first_set, no_button_sets):
    print "buttonify_bids(bid_set,first_set,no_button_sets)"
    actions = []
    action = {}
    for bid in bid_set:
        action = {
            "name": "bid_{}".format(no_button_sets),
                    "text": str(bid),
                    "type": "button",
                    "value": int(bid)
        }
        actions.append(action)
    if first_set:
        attachments = [
            {
                "title": "What's your bid for the round?",
                "fallback": "Place a bid.",
                "color": "#4CAF50",
                "callback_id": "buttonify_bids",
                "attachment_type": "default",
                "actions": actions
            }]
    else:
        attachments = [
            {
                "title": "",
                "fallback": "Place a bid.",
                "color": "#4CAF50",
                "callback_id": "buttonify_bids",
                "attachment_type": "default",
                "actions": actions
            }]
    return attachments
