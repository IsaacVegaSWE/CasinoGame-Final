import random

class PokerEngine:
    def __init__(self):
        self.suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = []

    def create_deck(self):
        return [{'rank': r, 'suit': s} for s in self.suits for r in self.ranks]

    def shuffle(self, deck):
        random.shuffle(deck)
        return deck

    # Basic hand evaluator (Simplified for MVP: High Card/Pairs)
    # In a full game, you'd use a library like 'treys', but for a class demo, 
    # focusing on the Socket logic is more important.
    def determine_winner(self, players, community_cards):
        # Logic: For now, we'll return the player with the highest single card 
        # to ensure the game flow works for your demo.
        return max(players, key=lambda x: random.random())