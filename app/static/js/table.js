/* ── Setup ─────────────────────────────────────────────────────────────── */
const socket = io({ transports: ['websocket', 'polling'] });
let gameState = null;

// ── Suit helpers ─────────────────────────────────────────────────────────
const SUIT_SYMBOL = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
const RED_SUITS = new Set(['hearts', 'diamonds']);

function makeCardEl(card, size = 'normal') {
  const el = document.createElement('div');
  el.className = 'card';
  if (!card) {
    el.classList.add('placeholder');
    return el;
  }
  if (card === 'back') {
    el.classList.add('back');
    return el;
  }
  el.classList.add(RED_SUITS.has(card.suit) ? 'red' : 'black');
  el.innerHTML = `<span class="rank">${card.rank}</span><span class="suit">${SUIT_SYMBOL[card.suit]}</span>`;
  return el;
}

// ── Card rendering ────────────────────────────────────────────────────────
function renderCommunity(cards) {
  const el = document.getElementById('community-cards');
  el.innerHTML = '';
  const count = cards ? cards.length : 0;
  for (let i = 0; i < 5; i++) {
    el.appendChild(makeCardEl(count > i ? cards[i] : null));
  }
}

function renderMyHand(cards) {
  const el = document.getElementById('my-cards');
  el.innerHTML = '';
  if (!cards || cards.length === 0) {
    el.appendChild(makeCardEl(null));
    el.appendChild(makeCardEl(null));
    return;
  }
  cards.forEach(c => el.appendChild(makeCardEl(c)));
}

// ── Seat Positions (oval layout) ──────────────────────────────────────────
function getSeatPositions(n) {
  const positions = [];
  const cx = 50, cy = 50;
  const rx = 58, ry = 68;
  for (let i = 0; i < n; i++) {
    const angle = (2 * Math.PI * i / n) - Math.PI / 2;
    positions.push({
      left: cx + rx * Math.cos(angle),
      top:  cy + ry * Math.sin(angle),
    });
  }
  return positions;
}

function renderSeats(state) {
  const container = document.getElementById('seats-container');
  const players = state.players;
  const positions = getSeatPositions(players.length);

  container.innerHTML = '';
  players.forEach((p, i) => {
    const pos = positions[i];
    const seat = document.createElement('div');
    seat.className = 'seat' +
      (p.is_current ? ' is-current' : '') +
      (p.is_dealer ? ' is-dealer' : '') +
      (p.folded ? ' folded' : '');
    seat.style.left = pos.left + '%';
    seat.style.top  = pos.top + '%';

    const avatarLetter = p.username.charAt(0).toUpperCase();

    // Hole cards above/below avatar depending on position
    const cardsHtml = () => {
      const div = document.createElement('div');
      div.className = 'seat-hole-cards';
      if (p.hole_cards && p.hole_cards.length) {
        p.hole_cards.forEach(c => div.appendChild(makeCardEl(c === null ? 'back' : c)));
      }
      return div;
    };

    const avatar = document.createElement('div');
    avatar.className = 'seat-avatar';
    avatar.textContent = avatarLetter;

    const name = document.createElement('div');
    name.className = 'seat-name';
    name.textContent = p.username + (p.user_id === MY_USER_ID ? ' (you)' : '');

    const chips = document.createElement('div');
    chips.className = 'seat-chips';
    chips.textContent = '⬡ ' + p.chips.toLocaleString();

    seat.appendChild(cardsHtml());
    seat.appendChild(avatar);
    seat.appendChild(name);
    seat.appendChild(chips);

    if (p.bet > 0) {
      const bet = document.createElement('div');
      bet.className = 'seat-bet';
      bet.textContent = 'bet: ' + p.bet.toLocaleString();
      seat.appendChild(bet);
    }
    if (p.all_in) {
      const ai = document.createElement('div');
      ai.className = 'badge badge-playing';
      ai.textContent = 'ALL IN';
      ai.style.fontSize = '0.6rem';
      seat.appendChild(ai);
    }

    container.appendChild(seat);
  });
}

// ── Update UI from state ──────────────────────────────────────────────────
function applyState(state) {
  gameState = state;
  document.getElementById('pot-val').textContent = state.pot.toLocaleString();
  document.getElementById('phase-label').textContent = state.phase.toUpperCase();

  renderCommunity(state.community_cards);
  renderSeats(state);

  // My player data
  const me = state.players.find(p => p.user_id === MY_USER_ID);
  if (me) {
    renderMyHand(me.hole_cards.includes(null) ? [] : me.hole_cards);
    document.getElementById('my-chips-val').textContent = me.chips.toLocaleString();
  }

  // Host controls
  const hostCtrl = document.getElementById('host-controls');
  if (IS_HOST) {
    hostCtrl.style.display = 'flex';
    const btnStart = document.getElementById('btn-start');
    const btnNext = document.getElementById('btn-next-hand');
    if (state.phase === 'waiting' || state.phase === 'showdown') {
      btnStart.style.display = state.phase === 'waiting' ? 'block' : 'none';
      btnNext.style.display = state.phase === 'showdown' ? 'block' : 'none';
    } else {
      btnStart.style.display = 'none';
      btnNext.style.display = 'none';
    }
  }

  // Action panel
  const isMyTurn = me && state.players.find(p => p.user_id === MY_USER_ID && p.is_current);
  const actionPanel = document.getElementById('action-panel');
  if (isMyTurn && state.phase !== 'waiting' && state.phase !== 'showdown') {
    actionPanel.style.display = 'flex';
    const toCall = Math.max(0, state.current_bet - (me.bet || 0));
    document.getElementById('to-call-val').textContent = toCall.toLocaleString();
    document.getElementById('my-bet-val').textContent = (me.bet || 0).toLocaleString();

    // Show/hide check vs call
    document.getElementById('btn-check').style.display = toCall === 0 ? 'block' : 'none';
    document.getElementById('btn-call').style.display = toCall > 0 ? 'block' : 'none';
    document.getElementById('btn-call').textContent = `Call ${toCall.toLocaleString()}`;

    // Raise slider
    const minRaise = state.current_bet + state.min_raise;
    const maxBet = (me.chips || 0) + (me.bet || 0);
    const slider = document.getElementById('raise-slider');
    slider.min = minRaise;
    slider.max = maxBet;
    slider.value = Math.max(minRaise, slider.value);
    document.getElementById('raise-input').value = slider.value;
    document.getElementById('raise-label').textContent = parseInt(slider.value).toLocaleString();
  } else {
    actionPanel.style.display = 'none';
    document.getElementById('raise-control').style.display = 'none';
  }

  // Showdown
  if (state.phase === 'showdown' && state.winner_info) {
    showShowdown(state.winner_info);
  }
}

// ── Showdown overlay ──────────────────────────────────────────────────────
function showShowdown(wi) {
  const overlay = document.getElementById('showdown-overlay');
  const body = document.getElementById('showdown-body');
  overlay.style.display = 'flex';

  let html = '';
  wi.winners.forEach(w => {
    html += `<div class="winner-row">
      <div class="winner-name">🏆 ${w.username}</div>
      <div class="winner-hand">${wi.hand_name}</div>
      <div class="winner-pot">+${w.chips_won.toLocaleString()} chips</div>
    </div>`;
  });

  if (wi.all_hands && wi.all_hands.length) {
    html += '<div class="showdown-hands">';
    wi.all_hands.forEach(h => {
      if (!h.hole_cards || h.hole_cards.length === 0) return;
      html += `<div class="hand-reveal"><div class="hand-reveal-name">${h.username}</div><div class="hand-reveal-cards" id="hr_${h.user_id}"></div></div>`;
    });
    html += '</div>';
  }
  body.innerHTML = html;

  if (wi.all_hands) {
    wi.all_hands.forEach(h => {
      const el = document.getElementById(`hr_${h.user_id}`);
      if (el && h.hole_cards) {
        h.hole_cards.forEach(c => el.appendChild(makeCardEl(c)));
      }
    });
  }
}

function hideShowdown() {
  document.getElementById('showdown-overlay').style.display = 'none';
}

// ── Chat ──────────────────────────────────────────────────────────────────
function appendChat(msg, isSystem = false) {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg' + (isSystem ? ' sys-msg' : '');
  if (isSystem) {
    div.innerHTML = `<span class="chat-text">${escHtml(msg)}</span>`;
  } else {
    div.innerHTML = `<span class="chat-user">${escHtml(msg.username)}</span>: <span class="chat-text">${escHtml(msg.content)}</span>`;
  }
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Actions ───────────────────────────────────────────────────────────────
function sendAction(action, amount) {
  socket.emit('player_action', { room_id: ROOM_ID, action, amount: amount || 0 });
}

document.getElementById('btn-fold').onclick = () => sendAction('fold');
document.getElementById('btn-check').onclick = () => sendAction('check');
document.getElementById('btn-call').onclick = () => sendAction('call');
document.getElementById('btn-allin').onclick = () => sendAction('allin');

document.getElementById('btn-raise').onclick = () => {
  const rc = document.getElementById('raise-control');
  rc.style.display = rc.style.display === 'none' ? 'flex' : 'none';
};

document.getElementById('btn-raise-confirm').onclick = () => {
  const val = parseInt(document.getElementById('raise-input').value);
  sendAction('raise', val);
  document.getElementById('raise-control').style.display = 'none';
};

document.getElementById('raise-slider').oninput = function() {
  document.getElementById('raise-input').value = this.value;
  document.getElementById('raise-label').textContent = parseInt(this.value).toLocaleString();
};
document.getElementById('raise-input').oninput = function() {
  document.getElementById('raise-slider').value = this.value;
  document.getElementById('raise-label').textContent = parseInt(this.value).toLocaleString();
};

// Host buttons
if (IS_HOST) {
  document.getElementById('btn-start').onclick = () => socket.emit('start_game', { room_id: ROOM_ID });
  document.getElementById('btn-next-hand').onclick = () => {
    hideShowdown();
    socket.emit('next_hand', { room_id: ROOM_ID });
  };
  const overlay_next = document.getElementById('btn-next-hand-overlay');
  if (overlay_next) {
    overlay_next.onclick = () => {
      hideShowdown();
      socket.emit('next_hand', { room_id: ROOM_ID });
    };
  }
}

// Leave button
document.getElementById('leave-btn').onclick = (e) => {
  e.preventDefault();
  socket.emit('leave_table', { room_id: ROOM_ID });
  setTimeout(() => { window.location.href = '/lobby'; }, 200);
};

// Chat
document.getElementById('btn-send').onclick = sendChat;
document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendChat();
});
function sendChat() {
  const input = document.getElementById('chat-input');
  const content = input.value.trim();
  if (!content) return;
  socket.emit('send_chat', { room_id: ROOM_ID, content });
  input.value = '';
}

// ── Socket events ─────────────────────────────────────────────────────────
socket.on('connect', () => {
  socket.emit('join_table', { room_id: ROOM_ID });
});

socket.on('game_state', state => {
  applyState(state);
});

socket.on('chat_history', messages => {
  messages.forEach(m => appendChat(m));
});

socket.on('chat_message', msg => {
  appendChat(msg);
});

socket.on('system_msg', data => {
  appendChat(data.msg, true);
});

socket.on('showdown', wi => {
  if (wi && wi.winners) showShowdown(wi);
});

socket.on('error', data => {
  appendChat('⚠ ' + data.msg, true);
});

socket.on('game_over', () => {
  appendChat('🏁 Game over! Returning to lobby in 5 seconds…', true);
  setTimeout(() => { window.location.href = '/lobby'; }, 5000);
});
