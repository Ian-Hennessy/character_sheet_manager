"""
Creates a Flask blueprint named /auth. We will handle all 
authentication, login/signup and password security via werkzeug
here.
"""

import functools 

from flask import (
    Blueprint, flash, g, redirect, 
    render_template, request, session, url_for
)

from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

# create the bluepring 
bp = Blueprint('auth', __name__, url_prefix="/auth")

@bp.route("/register", methods=('GET','POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()

        error = None

        if not username:
            error = 'Oops! You rolled a nat 1 on persuasion. Please enter a username.'
        if not password:
            error = 'Password rolled a nat 20 stealth. Please enter it at disadvantage...'

        if error is None: 
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                db.commit()
            except db.IntegrityError:
                error = f"Username {username} is already registered! Please pick a new one, or check your spelling."

            else:
                return redirect(url_for("auth.login"))
            
        flash(error)

    return render_template("auth/regiser.html")

@bp.route("/login", methods=('POST','GET'))
def login():
    if request_meth