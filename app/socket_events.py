from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import User, GameSession, ChatMessage, HandHistory
from app.poker_engine import PokerGame, GamePhase

# In-memory store of active games keyed by room_id
active_games: dict[str, PokerGame] = {}
# Map socket sid -> (user_id, room_id)
sid_map: dict[str, tuple] = {}


def get_or_create_game(room):
    if room.room_id not in active_games:
        active_games[room.room_id] = PokerGame(
            room.room_id,
            small_blind=room.small_blind,
            big_blind=room.big_blind,
        )
    return active_games[room.room_id]


def broadcast_state(game, room_id):
    """Send personalized game state to every player in the room."""
    for p in game.players:
        state = game.public_state(viewer_user_id=p['user_id'])
        emit('game_state', state, room=f"user_{p['user_id']}_{room_id}")
    # Also emit a general state for spectators (no hole cards)
    emit('game_state', game.public_state(), room=room_id, include_self=False)


def emit_to_player(user_id, room_id, event, data):
    emit(event, data, room=f"user_{user_id}_{room_id}")


@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    info = sid_map.pop(request.sid, None)
    if info:
        user_id, room_id = info
        game = active_games.get(room_id)
        if game:
            p = game.get_player(user_id)
            if p:
                p['connected'] = False
            broadcast_state(game, room_id)


@socketio.on('join_table')
def on_join_table(data):
    room_id = data.get('room_id')
    room = GameSession.query.filter_by(room_id=room_id).first()
    if not room:
        emit('error', {'msg': 'Room not found'})
        return

    user = User.query.get(current_user.id)
    game = get_or_create_game(room)

    # Join socket rooms
    join_room(room_id)
    join_room(f"user_{user.id}_{room_id}")
    sid_map[request.sid] = (user.id, room_id)

    # Add to game if not already in and has chips
    if not game.get_player(user.id):
        if user.chips < room.buy_in:
            emit('error', {'msg': 'Not enough chips'})
            return
        if len(game.players) >= room.max_players:
            emit('error', {'msg': 'Table is full'})
            return
        # Deduct buy-in
        buy_in_amount = min(room.buy_in, user.chips)
        user.chips -= buy_in_amount
        db.session.commit()
        game.add_player(user.id, user.username, buy_in_amount, user.avatar_seed or '')
    else:
        p = game.get_player(user.id)
        p['connected'] = True

    # Send recent chat
    recent_msgs = ChatMessage.query.filter_by(room_id=room.id).order_by(ChatMessage.timestamp.desc()).limit(30).all()
    emit('chat_history', [m.to_dict() for m in reversed(recent_msgs)])

    broadcast_state(game, room_id)
    emit('system_msg', {'msg': f"{user.username} joined the table"}, room=room_id)


@socketio.on('leave_table')
def on_leave_table(data):
    room_id = data.get('room_id')
    room = GameSession.query.filter_by(room_id=room_id).first()
    if not room:
        return

    user = User.query.get(current_user.id)
    game = active_games.get(room_id)

    if game:
        p = game.get_player(user.id)
        if p and game.phase in (GamePhase.WAITING, GamePhase.SHOWDOWN):
            # Return chips
            user.chips += p['chips']
            db.session.commit()
            game.remove_player(user.id)
        elif p:
            p['folded'] = True
            p['connected'] = False

    leave_room(room_id)
    leave_room(f"user_{user.id}_{room_id}")
    sid_map.pop(request.sid, None)

    if game:
        broadcast_state(game, room_id)
    emit('system_msg', {'msg': f"{user.username} left the table"}, room=room_id)


@socketio.on('start_game')
def on_start_game(data):
    room_id = data.get('room_id')
    room = GameSession.query.filter_by(room_id=room_id).first()
    if not room or room.host_id != current_user.id:
        emit('error', {'msg': 'Only the host can start the game'})
        return

    game = active_games.get(room_id)
    if not game:
        emit('error', {'msg': 'No game found'})
        return

    if not game.can_start():
        emit('error', {'msg': 'Need at least 2 players'})
        return

    room.status = 'playing'
    db.session.commit()

    game.start_hand()
    broadcast_state(game, room_id)
    emit('system_msg', {'msg': '🃏 New hand started!'}, room=room_id)


@socketio.on('next_hand')
def on_next_hand(data):
    room_id = data.get('room_id')
    room = GameSession.query.filter_by(room_id=room_id).first()
    if not room or room.host_id != current_user.id:
        return

    game = active_games.get(room_id)
    if not game or game.phase != GamePhase.SHOWDOWN:
        return

    # Sync chip counts back to DB
    _sync_chips(game)

    # Remove broke players
    game.players = [p for p in game.players if p['chips'] > 0]

    if game.can_start():
        game.start_hand()
        broadcast_state(game, room_id)
        emit('system_msg', {'msg': '🃏 New hand!'}, room=room_id)
    else:
        room.status = 'finished'
        db.session.commit()
        emit('game_over', {}, room=room_id)


@socketio.on('player_action')
def on_player_action(data):
    room_id = data.get('room_id')
    action = data.get('action')
    amount = data.get('amount', 0)

    game = active_games.get(room_id)
    if not game:
        return

    cp = game.current_player()
    if not cp or cp['user_id'] != current_user.id:
        emit('error', {'msg': 'Not your turn'})
        return

    ok = False
    if action == 'fold':
        ok, result = game.action_fold(current_user.id)
    elif action == 'check':
        ok, result = game.action_check(current_user.id)
    elif action == 'call':
        ok, result = game.action_call(current_user.id)
    elif action == 'raise':
        ok, result = game.action_raise(current_user.id, int(amount))
    elif action == 'allin':
        ok, result = game.action_all_in(current_user.id)
    else:
        emit('error', {'msg': 'Unknown action'})
        return

    if not ok:
        emit('error', {'msg': result})
        return

    if result == 'showdown':
        _handle_showdown(game, room_id)
    else:
        broadcast_state(game, room_id)


def _handle_showdown(game, room_id):
    room = GameSession.query.filter_by(room_id=room_id).first()
    wi = game.winner_info
    if wi:
        for w in wi['winners']:
            user = User.query.get(w['user_id'])
            if user:
                user.games_won += 1
        for p in game.players:
            user = User.query.get(p['user_id'])
            if user:
                user.games_played += 1
                user.total_winnings += p['chips']
        # Log hand
        if wi['winners']:
            hh = HandHistory(
                room_id=room_id,
                winner_id=wi['winners'][0]['user_id'],
                pot_size=wi['pot'],
                hand_description=wi['hand_name'],
            )
            db.session.add(hh)
        db.session.commit()

    broadcast_state(game, room_id)
    if room and room.host_id:
        emit('showdown', wi or {}, room=room_id)


def _sync_chips(game):
    for p in game.players:
        user = User.query.get(p['user_id'])
        if user:
            user.chips += p['chips']
            p['chips'] = 0
    db.session.commit()


@socketio.on('send_chat')
def on_chat(data):
    room_id = data.get('room_id')
    content = data.get('content', '').strip()[:500]
    if not content:
        return

    room = GameSession.query.filter_by(room_id=room_id).first()
    user = User.query.get(current_user.id)

    msg = ChatMessage(content=content, user_id=user.id, room_id=room.id if room else None)
    db.session.add(msg)
    db.session.commit()

    emit('chat_message', msg.to_dict(), room=room_id)
