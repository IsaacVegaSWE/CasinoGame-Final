from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, GameSession
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.lobby'))
    return redirect(url_for('auth.login'))


@main_bp.route('/lobby')
@login_required
def lobby():
    rooms = GameSession.query.filter(GameSession.status.in_(['waiting', 'playing'])).order_by(GameSession.created_at.desc()).all()
    return render_template('lobby.html', rooms=rooms)


@main_bp.route('/leaderboard')
@login_required
def leaderboard():
    players = User.query.order_by(User.chips.desc()).limit(20).all()
    return render_template('leaderboard.html', players=players)


@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)
