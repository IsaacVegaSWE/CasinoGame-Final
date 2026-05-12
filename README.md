# ♠ Royal Flush – Online Poker

A real-time multiplayer Texas Hold'em poker web app built with Flask, Socket.IO, and SQLite/PostgreSQL.

## Features
- 🃏 Real-time No-Limit Texas Hold'em (WebSocket via Socket.IO)
- 👤 User registration & login with bcrypt-hashed/salted passwords
- 🏆 Leaderboard with win rates and chip counts
- 💬 In-game live chat
- 🎰 Multiple tables with configurable blinds and buy-ins
- 📊 Player profile stats (hands played, won, win rate)
- 🔒 CSRF protection on all forms

---

## Local Development

```bash
# 1. Clone / enter directory
cd poker_app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and change SECRET_KEY

# 5. Run
python run.py
# Visit http://localhost:5000
```

---

## Deployment – Render (Recommended for WebSockets)

> **Why Render, not Vercel/Cloudflare Pages?**
> Vercel and Cloudflare Pages are serverless/edge platforms. They do **not** support persistent WebSocket connections (Socket.IO) or long-running Python processes. Render's free tier supports both, making it the right choice for this real-time app.

### Steps

1. **Push to GitHub** (public or private repo)

2. **Sign up at [render.com](https://render.com)** (free)

3. **New → Web Service**
   - Connect your GitHub repo
   - Language: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn --worker-class eventlet -w 1 run:app`

4. **Environment Variables** (in Render dashboard → Environment):
   ```
   SECRET_KEY=your-random-secret-here
   DATABASE_URL=sqlite:///poker.db
   ```
   For a persistent database, add a **PostgreSQL** addon (free tier) and set `DATABASE_URL` to the provided connection string.

5. **Deploy** — Render will auto-deploy on every push.

### Upgrading to PostgreSQL on Render

1. In Render dashboard: New → PostgreSQL (free tier)
2. Copy the "Internal Database URL"
3. Set as `DATABASE_URL` environment variable on your web service
4. Add `psycopg2-binary` to requirements.txt

---

## Alternative: Railway

```
railway login
railway init
railway add
railway up
```
Set `SECRET_KEY` and `DATABASE_URL` in Railway environment settings.

---

## Project Structure

```
poker_app/
├── run.py                  # Entry point
├── requirements.txt
├── Procfile                # For Heroku/Render/Railway
├── .env.example
├── app/
│   ├── __init__.py         # App factory
│   ├── models.py           # SQLAlchemy models (User, GameSession, ChatMessage)
│   ├── poker_engine.py     # Full Texas Hold'em game engine
│   ├── socket_events.py    # Socket.IO real-time event handlers
│   ├── forms.py            # WTForms (register, login)
│   ├── routes/
│   │   ├── auth.py         # /register, /login, /logout
│   │   ├── main.py         # /lobby, /leaderboard, /profile
│   │   └── game.py         # /create_room, /table/<id>, /join/<id>
│   ├── templates/
│   │   ├── base.html
│   │   ├── lobby.html
│   │   ├── leaderboard.html
│   │   ├── profile.html
│   │   ├── table.html
│   │   └── auth/
│   │       ├── login.html
│   │       └── register.html
│   └── static/
│       ├── css/
│       │   ├── main.css    # Global styles (dark luxury casino aesthetic)
│       │   └── table.css   # Poker table, cards, seats
│       └── js/
│           └── table.js    # Socket.IO client, card rendering, game UI
```

---

## Security

- Passwords hashed with **bcrypt** (salt auto-generated per user)
- CSRF tokens on all POST forms (Flask-WTF)
- Session cookies (Flask-Login)
- SQL injection protection via SQLAlchemy ORM

---

## Game Rules

Standard No-Limit Texas Hold'em:
- Each player gets 2 hole cards
- 3 community cards (flop), then 1 (turn), then 1 (river)
- Best 5-card hand from 7 cards wins
- Blinds: small blind + big blind posted automatically
- Actions: Fold, Check, Call, Raise, All-In
- **Host** controls starting each hand and dealing next hand
