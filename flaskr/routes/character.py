"""
Character management routes.
Handles character creation, viewing, updating and deletion with validation and error handling.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, 
    jsonify, flash, current_app
)
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
import json
import logging
from functools import wraps

from flaskr.db import get_db
from flaskr.character_factory import create_character
from flaskr.data.base_classes import DndClass
from flaskr.data.base_species import DndSpecies
from flaskr.character import Character

bp = Blueprint('character', __name__, url_prefix='/character')
logger = logging.getLogger(__name__)

# AUTH DECORATOR

# define database 

def login_required(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def character_owner_required(f):
    """Verify user owns the character being accessed."""
    @wraps(f)
    
    def decorated_function(*args, **kwargs):
        db = get_db()
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        char_id = kwargs.get('character_id')
        if not char_id:
            raise BadRequest("Character ID required")
        

        char = db.execute(
            'SELECT user_id FROM characters WHERE id = ?',
            (char_id,)
        ).fetchone()
        
        if not char:
            raise NotFound("Character not found")
        
        if char['user_id'] != session['user_id']:
            raise Forbidden("You don't own this character")
        
        return f(*args, **kwargs)
    return decorated_function


# CHARACTER LIST

@bp.route('/', methods=['GET'])
def home():
    """Display user's character list (homepage after login)."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    
    characters = db.execute(
        '''SELECT id, name, class, species, level, data 
           FROM characters 
           WHERE user_id = ? 
           ORDER BY updated DESC''',
        (session['user_id'],)
    ).fetchall()
    
    # Parse character data for display
    char_list = []
    for char in characters:
        try:
            data = json.loads(char['data'])
            char_list.append({
                'id': char['id'],
                'name': char['name'],
                'class': char['class'],
                'species': char['species'],
                'level': char['level'],
                'hp': data.get('hit_points', 0),
                'max_hp': data.get('max_hit_points', 0),
                'ac': data.get('armor_class', 10),
            })
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing character {char['id']}: {e}")
            continue
    
    return render_template('character/home.html', characters=char_list)


# CHARACTER CREATION (3-STEP FORM)

@bp.route('/create/step1', methods=['GET', 'POST'])
@login_required
def create_step1():

    """Step 1: Character name."""
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        
        # Validation
        if not name:
            flash('Character name is required', 'error')
            return render_template('character/create_step1.html')
        
        if len(name) > 100:
            flash('Character name must be 100 characters or less', 'error')
            return render_template('character/create_step1.html')
        
        # Check for duplicate names for this user

        existing = db.execute(
            'SELECT id FROM characters WHERE user_id = ? AND name = ?',
            (session['user_id'], name)
        ).fetchone()
        
        if existing:
            flash('You already have a character with this name', 'error')
            return render_template('character/create_step1.html')
        
        # Store in session for multi-step form
        session['char_creation'] = {'name': name}
        session.modified = True
        
        return redirect(url_for('character.create_step2'))
    
    return render_template('character/create_step1.html')


@bp.route('/create/step2', methods=['GET', 'POST'])
@login_required
def create_step2():

    """Step 2: Class & Species selection."""
    db = get_db()
    if 'char_creation' not in session:
        return redirect(url_for('character.create_step1'))
    
    try:
        available_classes = DndClass.get_available_classes()
        available_species = DndSpecies.get_available_species()
    except Exception as e:
        logger.error(f"Error fetching classes/species: {e}")
        flash('Error loading class/species data. Please try again.', 'error')
        return redirect(url_for('character.create_step1'))
    
    if request.method == 'POST':
        class_name = request.form.get('class', '').strip()
        species_name = request.form.get('species', '').strip()
        level = request.form.get('level', '1').strip()
        
        # Validation
        if not class_name or class_name not in available_classes:
            flash('Invalid class selection', 'error')
            return render_template(
                'character/create_step2.html',
                available_classes=available_classes,
                available_species=available_species
            )
        
        if not species_name or species_name not in available_species:
            flash('Invalid species selection', 'error')
            return render_template(
                'character/create_step2.html',
                available_classes=available_classes,
                available_species=available_species
            )
        
        try:
            level = int(level)
            if level < 1 or level > 20:
                raise ValueError("Level must be 1-20")
        except (ValueError, TypeError):
            flash('Invalid level. Must be 1-20', 'error')
            return render_template(
                'character/create_step2.html',
                available_classes=available_classes,
                available_species=available_species
            )
        
        # Update session
        session['char_creation']['class'] = class_name
        session['char_creation']['species'] = species_name
        session['char_creation']['level'] = level
        session.modified = True
        
        return redirect(url_for('character.create_step3'))
    
    return render_template(
        'character/create_step2.html',
        available_classes=available_classes,
        available_species=available_species
    )


@bp.route('/create/step3', methods=['GET', 'POST'])
@login_required
def create_step3():


    """Step 3: Ability scores (optional)."""
    if 'char_creation' not in session or 'class' not in session['char_creation']:
        return redirect(url_for('character.create_step1'))
    if request.method == 'POST':
        # Get ability scores or use defaults
        ability_scores = None
        use_defaults = request.form.get('use_defaults') == 'on'
        
        if not use_defaults:
            try:
                ability_scores = [
                    int(request.form.get(f'ability_{i}', '10'))
                    for i in range(6)
                ]
                
                # Validate range
                for score in ability_scores:
                    if score < 3 or score > 18:
                        flash('All ability scores must be between 3 and 18', 'error')
                        return render_template('character/create_step3.html')
            except (ValueError, TypeError):
                flash('Invalid ability score input', 'error')
                return render_template('character/create_step3.html')
        
        # Create character
        db = get_db()
        try:
            char_data = session['char_creation']
            character = create_character(
                name=char_data['name'],
                class_name=char_data['class'],
                species_name=char_data['species'],
                ability_scores=ability_scores,
                level=char_data.get('level', 1),
            )

            # Save to database
            db.execute(
                '''INSERT INTO characters 
                   (user_id, name, class, species, level, data, created, updated) 
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)''',
                (
                    session['user_id'],
                    character.data['name'],
                    char_data['class'],
                    char_data['species'],
                    char_data.get('level', 1),
                    json.dumps(character.data)
                )
            )
            db.commit()
            
            # Clean up session
            del session['char_creation']
            session.modified = True
            
            flash(f"Character '{character.data['name']}' created successfully!", 'success')
            return redirect(url_for('character.home'))
        
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            flash('Error creating character. Please try again.', 'error')
            return render_template('character/create_step3.html')
    
    return render_template('character/create_step3.html')


# VIEW CHARACTER

@bp.route('/<int:character_id>')
@login_required
@character_owner_required
def view(character_id):

    """Display character details."""

    db = get_db()
    char = db.execute(
        'SELECT * FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        character = Character(data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error loading character {character_id}: {e}")
        flash('Error loading character data', 'error')
        return redirect(url_for('character.home'))
    
    # Prepare display data
    ability_names = ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma']
    abilities = []
    for i, name in enumerate(ability_names):
        score = data['ability_scores'][i]
        mod = data['modifiers'][i]
        abilities.append({
            'name': name,
            'score': score,
            'modifier': mod,
            'sign': '+' if mod >= 0 else ''
        })
    
    # Skills with proficiency info
    skills = []
    if 'skills' in data:
        for skill_name, (proficient, modifier) in data['skills'].items():
            skills.append({
                'name': skill_name.title(),
                'proficient': proficient,
                'modifier': modifier,
                'sign': '+' if modifier >= 0 else ''
            })
    
    # Saving throws
    saving_throws = []
    if 'saving_throws' in data:
        for ability, (proficient, modifier) in data['saving_throws'].items():
            saving_throws.append({
                'ability': ability.title(),
                'proficient': proficient,
                'modifier': modifier,
                'sign': '+' if modifier >= 0 else ''
            })
    
    return render_template(
        'character/view.html',
        character_id=character_id,
        character=data,
        abilities=abilities,
        skills=sorted(skills, key=lambda x: x['name']),
        saving_throws=saving_throws
    )


# LEVEL UP

@bp.route('/<int:character_id>/levelup', methods=['POST'])
@login_required
@character_owner_required
def level_up(character_id):
    
    """Level up character."""

    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        current_level = data.get('level', 1)
        
        if current_level >= 20:
            return jsonify({'error': 'Character is already max level (20)'}), 400
        
        # Level up
        new_level = current_level + 1
        data['level'] = new_level
        
        # Recalculate proficiency bonus
        proficiency_bonuses = [2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6]
        data['proficiency_bonus'] = proficiency_bonuses[new_level - 1]
        
        # Add HP (hit die + CON modifier)
        hit_die = data.get('hit_die', 8)
        con_mod = data['modifiers'][2]
        
        import random
        hp_gain = max(1, random.randint(1, hit_die) + con_mod)
        data['hit_points'] = min(
            data['max_hit_points'] + hp_gain,
            data['max_hit_points']
        )
        
        # Save changes
        db.execute(
            'UPDATE characters SET data = ?, level = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(data), new_level, character_id)
        )
        db.commit()
        
        return jsonify({
            'success': True,
            'level': new_level,
            'hp': data['hit_points'],
            'max_hp': data['max_hit_points']
        })
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error leveling up character {character_id}: {e}")
        return jsonify({'error': 'Error leveling up character'}), 500


# INVENTORY MANAGEMENT

@bp.route('/<int:character_id>/inventory/add', methods=['POST'])
@login_required
@character_owner_required
def add_inventory_item(character_id):
    
    """Add item to inventory."""

    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        
        item_name = request.form.get('item_name', '').strip()
        item_type = request.form.get('item_type', 'misc').strip()
        
        if not item_name or len(item_name) > 100:
            return jsonify({'error': 'Invalid item name'}), 400
        
        # Initialize inventory structure if needed
        if 'inventory' not in data:
            data['inventory'] = {
                'armor': None,
                'weapons': [],
                'equipped_items': [],
                'backpack': []
            }
        
        # Add to backpack (simple implementation)
        data['inventory']['backpack'].append({
            'name': item_name,
            'type': item_type
        })
        
        db.execute(
            'UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(data), character_id)
        )
        db.commit()
        
        return jsonify({'success': True, 'item': item_name})
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error adding inventory item: {e}")
        return jsonify({'error': 'Error adding item'}), 500


@bp.route('/<int:character_id>/inventory/remove', methods=['POST'])
@login_required
@character_owner_required
def remove_inventory_item(character_id):
    
    """Remove item from inventory."""

    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        item_index = int(request.form.get('item_index', -1))
        
        if item_index < 0 or 'inventory' not in data:
            return jsonify({'error': 'Invalid item'}), 400
        
        backpack = data['inventory'].get('backpack', [])
        if item_index >= len(backpack):
            return jsonify({'error': 'Item not found'}), 404
        
        removed_item = backpack.pop(item_index)
        
        db.execute(
            'UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(data), character_id)
        )
        db.commit()
        
        return jsonify({'success': True, 'removed': removed_item['name']})
    
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Error removing inventory item: {e}")
        return jsonify({'error': 'Error removing item'}), 500


# FEATURES & FEATS MANAGEMENT

@bp.route('/<int:character_id>/features', methods=['GET'])
@login_required
@character_owner_required
def view_features(character_id):
    
    """View character features and feats."""

    db = get_db()
    char = db.execute(
        'SELECT * FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        features = data.get('features', [])
        feats = data.get('feats', [])
    except json.JSONDecodeError as e:
        logger.error(f"Error loading features: {e}")
        flash('Error loading character features', 'error')
        return redirect(url_for('character.view', character_id=character_id))
    
    return render_template(
        'character/features.html',
        character_id=character_id,
        character=data,
        features=features,
        feats=feats
    )


@bp.route('/<int:character_id>/feats/add', methods=['POST'])
@login_required
@character_owner_required
def add_feat(character_id):
    
    """Add feat to character."""

    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        
        feat_name = request.form.get('feat_name', '').strip()
        feat_description = request.form.get('feat_description', '').strip()
        
        if not feat_name or len(feat_name) > 100:
            return jsonify({'error': 'Invalid feat name'}), 400
        
        if 'feats' not in data:
            data['feats'] = []
        
        data['feats'].append({
            'name': feat_name,
            'description': feat_description
        })
        
        db.execute(
            'UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(data), character_id)
        )
        db.commit()
        
        return jsonify({'success': True, 'feat': feat_name})
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error adding feat: {e}")
        return jsonify({'error': 'Error adding feat'}), 500


@bp.route('/<int:character_id>/feats/<int:feat_index>/remove', methods=['POST'])
@login_required
@character_owner_required
def remove_feat(character_id, feat_index):
    
    """Remove feat from character."""

    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    try:
        data = json.loads(char['data'])
        
        if 'feats' not in data or feat_index < 0 or feat_index >= len(data['feats']):
            return jsonify({'error': 'Feat not found'}), 404
        
        removed_feat = data['feats'].pop(feat_index)
        
        db.execute(
            'UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(data), character_id)
        )
        db.commit()
        
        return jsonify({'success': True, 'removed': removed_feat['name']})
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error removing feat: {e}")
        return jsonify({'error': 'Error removing feat'}), 500


# CHARACTER DELETION (SAFE)

@bp.route('/<int:character_id>/delete', methods=['GET', 'POST'])
@login_required
@character_owner_required
def delete_confirm(character_id):
    
    """Confirm character deletion (requires "DELETE" confirmation)."""

    db = get_db()
    char = db.execute(
        'SELECT name FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()
    
    if request.method == 'POST':
        confirmation = request.form.get('confirmation', '').strip()
        
        # Require user to type "DELETE"
        if confirmation != 'DELETE':
            flash('You must type "DELETE" to confirm character deletion', 'error')
            return render_template('character/delete_confirm.html', character_id=character_id, character_name=char['name'])
        
        try:
            # Delete character
            db.execute('DELETE FROM characters WHERE id = ?', (character_id,))
            db.commit()
            
            flash(f"Character '{char['name']}' has been permanently deleted", 'success')
            return redirect(url_for('character.home'))
        
        except Exception as e:
            logger.error(f"Error deleting character {character_id}: {e}")
            flash('Error deleting character. Please try again.', 'error')
            return render_template('character/delete_confirm.html', character_id=character_id, character_name=char['name'])
    
    return render_template('character/delete_confirm.html', character_id=character_id, character_name=char['name'])


# ERROR HANDLERS

@bp.errorhandler(NotFound)
def handle_not_found(e):
    """Handle 404 errors."""
    flash('Resource not found', 'error')
    return redirect(url_for('character.home'))


@bp.errorhandler(Forbidden)
def handle_forbidden(e):
    """Handle 403 errors."""
    flash('Access denied', 'error')
    return redirect(url_for('character.home'))
