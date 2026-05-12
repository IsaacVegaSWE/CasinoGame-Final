from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    chips = db.Column(db.Integer, default=10000)
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    total_winnings = db.Column(db.Integer, default=0)
    avatar_seed = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    messages = db.relationship('ChatMessage', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.games_won / self.games_played) * 100, 1)


class GameSession(db.Model):
    __tablename__ = 'game_sessions'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    max_players = db.Column(db.Integer, default=6)
    small_blind = db.Column(db.Integer, default=50)
    big_blind = db.Column(db.Integer, default=100)
    buy_in = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    messages = db.relationship('ChatMessage', backref='room', lazy=True)


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'username': self.author.username,
            'timestamp': self.timestamp.strftime('%H:%M'),
        }


class HandHistory(db.Model):
    __tablename__ = 'hand_history'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(20), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    pot_size = db.Column(db.Integer, default=0)
    hand_description = db.Column(db.String(100), nullable=True)
    played_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
