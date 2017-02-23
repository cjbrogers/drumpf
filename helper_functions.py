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

def interactiformat(cards):
    print "interactiformat(cards)"
    formatted_cards = []
    for idx, card in enumerate(cards):
        if len(card) == 2:
            formatted_cards.append("{}:{}:  ".format(card[0], card[1]))
        else:
            formatted_cards.append(":{}:  ".format(card))
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

def interactify(cards):
    print "interactify(cards)"
    actions = []
    action = {}
    for idx, card in enumerate(cards):
        action = {"name":card,"text":card,"type":"button","value":idx}
        actions.append(action)
    attachments =[{"title":"Your cards good sir/mam:", "fallback":"Your interface does not support interactive messages.", "callback_id":"interactify", "attachment_type":"default", "actions":actions}]
    print "  attachments: ",attachments
    return attachments
    # TODO: verify this ^^
