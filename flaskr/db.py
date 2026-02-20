"""
Handles various Database tasks via sqlite. 
Manages creating, clearing, closing and updating db.
"""

import sqlite3
import json
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


def create_character(user_id, name, data_dict):
    """Insert a new character for `user_id`. `data_dict` is a Python dict
    with character fields (will be JSON-encoded).
    Returns the new character id.
    """
    db = get_db()
    cur = db.execute(
        'INSERT INTO characters (user_id, name, data, updated) VALUES (?, ?, ?, ?)',
        (user_id, name, json.dumps(data_dict), datetime.utcnow())
    )
    db.commit()
    return cur.lastrowid


def get_characters_for_user(user_id):
    """Return a list of characters (dicts) for a given user_id."""
    db = get_db()
    rows = db.execute(
        'SELECT id, user_id, name, data, created, updated FROM characters WHERE user_id = ? ORDER BY created DESC',
        (user_id,)
    ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        try:
            item['data'] = json.loads(item['data'])
        except Exception:
            item['data'] = {}
        result.append(item)
    return result


def get_character(character_id):
    db = get_db()
    r = db.execute(
        'SELECT id, user_id, name, data, created, updated FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    if r is None:
        return None
    item = dict(r)
    try:
        item['data'] = json.loads(item['data'])
    except Exception:
        item['data'] = {}
    return item


def update_character(character_id, data_dict, name=None):
    """Update character `data` (JSON) and optionally `name`."""
    db = get_db()
    if name is None:
        db.execute(
            'UPDATE characters SET data = ?, updated = ? WHERE id = ?',
            (json.dumps(data_dict), datetime.utcnow(), character_id)
        )
    else:
        db.execute(
            'UPDATE characters SET name = ?, data = ?, updated = ? WHERE id = ?',
            (name, json.dumps(data_dict), datetime.utcnow(), character_id)
        )
    db.commit()


def delete_character(character_id):
    db = get_db()
    db.execute('DELETE FROM characters WHERE id = ?', (character_id,))
    db.commit()

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

