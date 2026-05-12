import random
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User
from app.forms import RegisterForm, LoginForm

auth_bp = Blueprint('auth', __name__)

AVATAR_SEEDS = ['pixel', 'nova', 'ring', 'solar', 'cosmic', 'ember', 'frost', 'thunder', 'vortex', 'prism']


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.lobby'))
    form = RegisterForm()
    if form.validate_on_submit():
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=pw_hash,
            chips=10000,
            avatar_seed=random.choice(AVATAR_SEEDS) + str(random.randint(1, 99)),
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created! Welcome to the table.', 'success')
        return redirect(url_for('main.lobby'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.lobby'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.lobby'))
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
