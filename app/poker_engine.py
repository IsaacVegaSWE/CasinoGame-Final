import random
from itertools import combinations
from enum import IntEnum


RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['spades', 'hearts', 'diamonds', 'clubs']
RANK_VALUES = {r: i for i, r in enumerate(RANKS)}


class HandRank(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


HAND_NAMES = {
    HandRank.HIGH_CARD: "High Card",
    HandRank.ONE_PAIR: "One Pair",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.THREE_OF_A_KIND: "Three of a Kind",
    HandRank.STRAIGHT: "Straight",
    HandRank.FLUSH: "Flush",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FOUR_OF_A_KIND: "Four of a Kind",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    HandRank.ROYAL_FLUSH: "Royal Flush",
}


def make_deck():
    return [{'rank': r, 'suit': s} for s in SUITS for r in RANKS]


def card_value(card):
    return RANK_VALUES[card['rank']]


def evaluate_5(cards):
    """Evaluate exactly 5 cards and return (HandRank, tiebreaker_list)."""
    vals = sorted([card_value(c) for c in cards], reverse=True)
    suits = [c['suit'] for c in cards]
    is_flush = len(set(suits)) == 1
    is_straight = (vals == list(range(vals[0], vals[0] - 5, -1))) or (vals == [12, 3, 2, 1, 0])
    if vals == [12, 3, 2, 1, 0]:
        is_straight = True
        vals = [3, 2, 1, 0, -1]  # Ace-low straight

    from collections import Counter
    counts = Counter(vals)
    groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    group_sizes = [g[1] for g in groups]
    group_vals = [g[0] for g in groups]

    if is_straight and is_flush:
        if vals[0] == 12:
            return (HandRank.ROYAL_FLUSH, vals)
        return (HandRank.STRAIGHT_FLUSH, vals)
    if group_sizes[0] == 4:
        return (HandRank.FOUR_OF_A_KIND, group_vals)
    if group_sizes[:2] == [3, 2]:
        return (HandRank.FULL_HOUSE, group_vals)
    if is_flush:
        return (HandRank.FLUSH, vals)
    if is_straight:
        return (HandRank.STRAIGHT, vals)
    if group_sizes[0] == 3:
        return (HandRank.THREE_OF_A_KIND, group_vals)
    if group_sizes[:2] == [2, 2]:
        return (HandRank.TWO_PAIR, group_vals)
    if group_sizes[0] == 2:
        return (HandRank.ONE_PAIR, group_vals)
    return (HandRank.HIGH_CARD, vals)


def best_hand(hole_cards, community_cards):
    """Find the best 5-card hand from 7 cards."""
    all_cards = hole_cards + community_cards
    best = None
    best_combo = None
    for combo in combinations(all_cards, 5):
        result = evaluate_5(list(combo))
        if best is None or result > best:
            best = result
            best_combo = combo
    return best, list(best_combo)


def compare_hands(players_with_cards, community):
    """Return list of winner user_ids (can be multiple for ties)."""
    results = []
    for p in players_with_cards:
        score, _ = best_hand(p['hole_cards'], community)
        results.append((score, p['user_id']))
    best_score = max(r[0] for r in results)
    winners = [r[1] for r in results if r[0] == best_score]
    return winners, best_score


# ─── Game State ─────────────────────────────────────────────────────────────

class GamePhase:
    WAITING = 'waiting'
    PREFLOP = 'preflop'
    FLOP = 'flop'
    TURN = 'turn'
    RIVER = 'river'
    SHOWDOWN = 'showdown'


class PokerGame:
    def __init__(self, room_id, small_blind=50, big_blind=100):
        self.room_id = room_id
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.players = []       # list of player dicts
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.side_pots = []
        self.current_bet = 0
        self.phase = GamePhase.WAITING
        self.dealer_idx = 0
        self.current_player_idx = 0
        self.hand_num = 0
        self.last_action = None
        self.winner_info = None
        self.min_raise = big_blind

    # ── Player management ──────────────────────────────────────────────────

    def add_player(self, user_id, username, chips, avatar_seed=''):
        if any(p['user_id'] == user_id for p in self.players):
            return False
        self.players.append({
            'user_id': user_id,
            'username': username,
            'chips': chips,
            'hole_cards': [],
            'bet': 0,
            'total_bet': 0,  # total bet this hand
            'folded': False,
            'all_in': False,
            'sitting_out': False,
            'avatar_seed': avatar_seed,
            'connected': True,
        })
        return True

    def remove_player(self, user_id):
        self.players = [p for p in self.players if p['user_id'] != user_id]

    def get_player(self, user_id):
        for p in self.players:
            if p['user_id'] == user_id:
                return p
        return None

    # ── Game flow ──────────────────────────────────────────────────────────

    def can_start(self):
        active = [p for p in self.players if not p['sitting_out']]
        return len(active) >= 2

    def start_hand(self):
        active = [p for p in self.players if not p['sitting_out'] and p['chips'] > 0]
        if len(active) < 2:
            return False

        self.hand_num += 1
        self.deck = make_deck()
        random.shuffle(self.deck)
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.winner_info = None
        self.last_action = None
        self.min_raise = self.big_blind

        for p in self.players:
            p['hole_cards'] = []
            p['bet'] = 0
            p['total_bet'] = 0
            p['folded'] = p['chips'] == 0
            p['all_in'] = False

        # Deal 2 hole cards each
        for _ in range(2):
            for p in active:
                p['hole_cards'].append(self.deck.pop())

        # Move dealer button
        self.dealer_idx = self._next_active_idx(self.dealer_idx)

        # Post blinds
        sb_idx = self._next_active_idx(self.dealer_idx)
        bb_idx = self._next_active_idx(sb_idx)

        self._post_blind(sb_idx, self.small_blind)
        self._post_blind(bb_idx, self.big_blind)
        self.current_bet = self.big_blind
        self.min_raise = self.big_blind

        # Action starts left of BB
        self.current_player_idx = self._next_active_idx(bb_idx)
        self._mark_last_aggressor(bb_idx)  # BB gets to act again if no raise
        self.phase = GamePhase.PREFLOP
        return True

    def _post_blind(self, idx, amount):
        p = self.players[idx]
        actual = min(amount, p['chips'])
        p['chips'] -= actual
        p['bet'] = actual
        p['total_bet'] = actual
        self.pot += actual
        if p['chips'] == 0:
            p['all_in'] = True

    def _next_active_idx(self, from_idx):
        n = len(self.players)
        idx = (from_idx + 1) % n
        for _ in range(n):
            p = self.players[idx]
            if not p['folded'] and not p['sitting_out']:
                return idx
            idx = (idx + 1) % n
        return from_idx

    def _mark_last_aggressor(self, idx):
        self._last_aggressor = idx

    def active_players(self):
        return [p for p in self.players if not p['folded'] and not p['sitting_out']]

    # ── Actions ────────────────────────────────────────────────────────────

    def current_player(self):
        if self.current_player_idx < len(self.players):
            return self.players[self.current_player_idx]
        return None

    def action_fold(self, user_id):
        p = self._validate_action(user_id)
        if not p:
            return False, "Not your turn"
        p['folded'] = True
        self.last_action = {'user': p['username'], 'action': 'fold', 'amount': 0}
        return self._advance()

    def action_check(self, user_id):
        p = self._validate_action(user_id)
        if not p:
            return False, "Not your turn"
        if p['bet'] < self.current_bet:
            return False, "Cannot check, must call or raise"
        self.last_action = {'user': p['username'], 'action': 'check', 'amount': 0}
        return self._advance()

    def action_call(self, user_id):
        p = self._validate_action(user_id)
        if not p:
            return False, "Not your turn"
        to_call = min(self.current_bet - p['bet'], p['chips'])
        p['chips'] -= to_call
        p['bet'] += to_call
        p['total_bet'] += to_call
        self.pot += to_call
        if p['chips'] == 0:
            p['all_in'] = True
        self.last_action = {'user': p['username'], 'action': 'call', 'amount': to_call}
        return self._advance()

    def action_raise(self, user_id, amount):
        p = self._validate_action(user_id)
        if not p:
            return False, "Not your turn"
        total_needed = amount  # total bet this street
        if total_needed < self.current_bet + self.min_raise and p['chips'] + p['bet'] > total_needed:
            return False, f"Raise must be at least {self.current_bet + self.min_raise}"
        actual_add = min(total_needed - p['bet'], p['chips'])
        self.min_raise = total_needed - self.current_bet
        self.current_bet = total_needed
        p['chips'] -= actual_add
        p['bet'] += actual_add
        p['total_bet'] += actual_add
        self.pot += actual_add
        if p['chips'] == 0:
            p['all_in'] = True
        self._mark_last_aggressor(self.current_player_idx)
        self.last_action = {'user': p['username'], 'action': 'raise', 'amount': total_needed}
        return self._advance()

    def action_all_in(self, user_id):
        p = self._validate_action(user_id)
        if not p:
            return False, "Not your turn"
        amount = p['chips'] + p['bet']  # total bet
        return self.action_raise(user_id, amount)

    def _validate_action(self, user_id):
        cp = self.current_player()
        if cp and cp['user_id'] == user_id and not cp['folded']:
            return cp
        return None

    def _advance(self):
        """Move to next player or next phase."""
        active = self.active_players()

        # Only one player left — they win
        if len(active) == 1:
            return self._award_pot(active)

        # All remaining non-folded players are all-in or bets are equal
        if self._betting_complete():
            return self._next_phase()

        # Find next player
        n = len(self.players)
        idx = (self.current_player_idx + 1) % n
        for _ in range(n):
            p = self.players[idx]
            if not p['folded'] and not p['sitting_out'] and not p['all_in']:
                self.current_player_idx = idx
                return True, 'action'
            idx = (idx + 1) % n

        # Everyone all-in, run out board
        return self._next_phase()

    def _betting_complete(self):
        active = self.active_players()
        non_allin = [p for p in active if not p['all_in']]
        if not non_allin:
            return True
        # All non-allin players have matched current bet
        return all(p['bet'] == self.current_bet for p in non_allin)

    def _next_phase(self):
        # Reset bets for new street
        for p in self.players:
            p['bet'] = 0
        self.current_bet = 0
        self.min_raise = self.big_blind

        if self.phase == GamePhase.PREFLOP:
            self.community_cards = [self.deck.pop() for _ in range(3)]
            self.phase = GamePhase.FLOP
        elif self.phase == GamePhase.FLOP:
            self.community_cards.append(self.deck.pop())
            self.phase = GamePhase.TURN
        elif self.phase == GamePhase.TURN:
            self.community_cards.append(self.deck.pop())
            self.phase = GamePhase.RIVER
        elif self.phase == GamePhase.RIVER:
            self.phase = GamePhase.SHOWDOWN
            return self._showdown()
        else:
            return self._showdown()

        # First active player left of dealer acts first post-flop
        self.current_player_idx = self._next_active_idx(self.dealer_idx)
        return True, 'phase_change'

    def _showdown(self):
        active = self.active_players()
        players_data = [{'user_id': p['user_id'], 'hole_cards': p['hole_cards']} for p in active]
        winner_ids, best_score = compare_hands(players_data, self.community_cards)

        hand_name = HAND_NAMES.get(best_score[0], 'Unknown')
        winners = [p for p in active if p['user_id'] in winner_ids]
        share = self.pot // len(winners)
        remainder = self.pot % len(winners)

        for w in winners:
            w['chips'] += share
        winners[0]['chips'] += remainder  # give remainder to first winner

        self.winner_info = {
            'winners': [{'user_id': w['user_id'], 'username': w['username'], 'chips_won': share} for w in winners],
            'hand_name': hand_name,
            'pot': self.pot,
            'community': self.community_cards,
            'all_hands': [{'user_id': p['user_id'], 'username': p['username'], 'hole_cards': p['hole_cards']} for p in active],
        }
        self.phase = GamePhase.SHOWDOWN
        return True, 'showdown'

    def _award_pot(self, active):
        w = active[0]
        w['chips'] += self.pot
        self.winner_info = {
            'winners': [{'user_id': w['user_id'], 'username': w['username'], 'chips_won': self.pot}],
            'hand_name': 'Everyone else folded',
            'pot': self.pot,
            'community': self.community_cards,
            'all_hands': [],
        }
        self.phase = GamePhase.SHOWDOWN
        return True, 'showdown'

    # ── Serialization ──────────────────────────────────────────────────────

    def public_state(self, viewer_user_id=None):
        """Return game state, hiding hole cards of other players unless showdown."""
        players_out = []
        for p in self.players:
            reveal = (p['user_id'] == viewer_user_id or self.phase == GamePhase.SHOWDOWN)
            players_out.append({
                'user_id': p['user_id'],
                'username': p['username'],
                'chips': p['chips'],
                'bet': p['bet'],
                'folded': p['folded'],
                'all_in': p['all_in'],
                'avatar_seed': p['avatar_seed'],
                'connected': p['connected'],
                'hole_cards': p['hole_cards'] if reveal else [None] * len(p['hole_cards']),
                'is_current': not p['folded'] and not p['sitting_out'] and
                              self.players.index(p) == self.current_player_idx,
                'is_dealer': self.players.index(p) == self.dealer_idx,
            })
        return {
            'room_id': self.room_id,
            'phase': self.phase,
            'pot': self.pot,
            'current_bet': self.current_bet,
            'min_raise': self.min_raise,
            'community_cards': self.community_cards,
            'players': players_out,
            'hand_num': self.hand_num,
            'last_action': self.last_action,
            'winner_info': self.winner_info,
            'small_blind': self.small_blind,
            'big_blind': self.big_blind,
        }
