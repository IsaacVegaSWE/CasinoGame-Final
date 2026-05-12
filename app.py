from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, join_room, emit
from models import db, bcrypt, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///poker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create database tables
with app.app_context():
    db.create_all()

# --- HTTP ROUTES (Frontend Serving & Auth) ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')

        if action == 'register':
            if User.query.filter_by(username=username).first():
                flash('Username already exists!')
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please log in.')
                
        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('poker_table'))
            else:
                flash('Invalid credentials.')

    return render_template('login.html')

@app.route('/table')
def poker_table():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('table.html', username=session['username'])

# --- WEBSOCKETS (Real-Time Game Sync) ---

@socketio.on('join_table')
def handle_join(data):
    username = session.get('username')
    room = 'main_table'
    join_room(room)
    
    # Broadcast to everyone else that a new player arrived
    emit('player_joined', {'username': username}, room=room)
    
    # Send current table state back to the user who just joined
    emit('system_message', {'message': f'Welcome to the table, {username}!'}, to=request.sid)

if __name__ == '__main__':
    # Use eventlet or gevent for production, standard werkzeug for local dev
    socketio.run(app, debug=True, port=5000)