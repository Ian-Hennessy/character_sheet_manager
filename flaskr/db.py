"""
Handles various Database tasks via sqlite. 
Manages creating, clearing, closing and updating db.
"""

import sqlite3
from datetime import datetime 

import click 

from flask import current_app, g 

def get_db():
    if 'db' not in g: 
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db',None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    # Clear existing data and initialize a new database 
    init_db()
    click.echo("Database initialized!")

sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    # Tells Flask to run the close_db command
    # after returning response from server
    app.teardown_appcontext(close_db)

    # reveals the init-db command to the app 
    # it can be run by the client 
    app.cli.add_command(init_db_command)

