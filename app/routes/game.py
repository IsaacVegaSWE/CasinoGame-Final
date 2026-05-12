import random
import string
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import GameSession

game_bp = Blueprint('game', __name__)


def gen_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@game_bp.route('/create_room', methods=['POST'])
@login_required
def create_room():
    name = request.form.get('name', f"{current_user.username}'s Table").strip() or f"{current_user.username}'s Table"
    small_blind = int(request.form.get('small_blind', 50))
    big_blind = small_blind * 2
    buy_in = int(request.form.get('buy_in', 1000))
    max_players = int(request.form.get('max_players', 6))

    if current_user.chips < buy_in:
        flash('Not enough chips for that buy-in.', 'danger')
        return redirect(url_for('main.lobby'))

    room_id = gen_room_id()
    while GameSession.query.filter_by(room_id=room_id).first():
        room_id = gen_room_id()

    room = GameSession(
        room_id=room_id,
        name=name,
        small_blind=small_blind,
        big_blind=big_blind,
        buy_in=buy_in,
        max_players=max_players,
        host_id=current_user.id,
        status='waiting',
    )
    db.session.add(room)
    db.session.commit()
    return redirect(url_for('game.table', room_id=room_id))


@game_bp.route('/table/<room_id>')
@login_required
def table(room_id):
    room = GameSession.query.filter_by(room_id=room_id).first_or_404()
    return render_template('table.html', room=room, user=current_user)


@game_bp.route('/join/<room_id>')
@login_required
def join_room_redirect(room_id):
    room = GameSession.query.filter_by(room_id=room_id).first_or_404()
    if current_user.chips < room.buy_in:
        flash('Not enough chips to join this table.', 'danger')
        return redirect(url_for('main.lobby'))
    return redirect(url_for('game.table', room_id=room_id))
