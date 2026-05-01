"""
Character management routes.
Handles character creation, viewing, updating and deletion with validation and error handling.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, 
    jsonify, flash, current_app
)

from .. import utils
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
import json
import logging
from functools import wraps

from flaskr.db import get_db
from flaskr.character_factory import create_character
from flaskr.data.base_classes import DndClass
from flaskr.data.base_species import DndSpecies
from flaskr.data.api_utils import get_feature_detail, get_class_level_data, get_class_spells, get_spell_detail
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
        available_classes = utils._extract_index(utils._api_request(utils.ApiField.CLASSES), 'name')
        available_species = utils._extract_index(utils._api_request(utils.ApiField.RACES), 'name')
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


_POINT_COSTS = {8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9, 16:10, 17:11, 18:12, 19:13, 20:14}
_STANDARD_ARRAY = sorted([15, 14, 13, 12, 10, 8])
_VALID_PB_BUDGETS = {25, 27, 30}


@bp.route('/create/step3', methods=['GET', 'POST'])
@login_required
def create_step3():
    """Step 3: Ability scores — standard array, point buy, or manual."""
    if 'char_creation' not in session or 'class' not in session['char_creation']:
        return redirect(url_for('character.create_step1'))

    if request.method == 'POST':
        score_method = request.form.get('score_method', 'standard')

        # Parse raw scores from hidden inputs populated by JS
        try:
            ability_scores = [int(request.form.get(f'ability_{i}', '10')) for i in range(6)]
        except (ValueError, TypeError):
            flash('Invalid ability score input.', 'error')
            return render_template('character/create_step3.html', score_method=score_method)

        # Per-method validation
        if score_method == 'standard':
            if sorted(ability_scores) != _STANDARD_ARRAY:
                flash('Ability scores must use the standard array: 15, 14, 13, 12, 10, 8.', 'error')
                return render_template('character/create_step3.html', score_method=score_method)

        elif score_method == 'pointbuy':
            try:
                budget = int(request.form.get('pb_budget', '27'))
                if budget not in _VALID_PB_BUDGETS:
                    raise ValueError
            except (ValueError, TypeError):
                flash('Invalid point buy budget.', 'error')
                return render_template('character/create_step3.html', score_method=score_method)

            if any(s < 8 or s > 20 for s in ability_scores):
                flash('Point buy scores must each be between 8 and 20.', 'error')
                return render_template('character/create_step3.html', score_method=score_method)

            total_cost = sum(_POINT_COSTS.get(s, 999) for s in ability_scores)
            if total_cost != budget:
                flash(f'Point total ({total_cost}) does not match the selected budget ({budget}).', 'error')
                return render_template('character/create_step3.html', score_method=score_method)

        else:  # manual / rolled
            if any(s < 3 or s > 20 for s in ability_scores):
                flash('Manual ability scores must each be between 3 and 20.', 'error')
                return render_template('character/create_step3.html', score_method=score_method)

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
                    json.dumps(character.data),
                )
            )
            db.commit()

            del session['char_creation']
            session.modified = True

            flash(f"Character '{character.data['name']}' created successfully!", 'success')
            return redirect(url_for('character.home'))

        except Exception as e:
            logger.error(f"Error creating character: {e}")
            flash('Error creating character. Please try again.', 'error')
            return render_template('character/create_step3.html', score_method=score_method)

    return render_template('character/create_step3.html', score_method='standard')


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
                'key': skill_name,
                'name': skill_name.replace('_', ' ').title(),
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


# SKILL PROFICIENCY TOGGLE

@bp.route('/<int:character_id>/skills/<skill_name>/toggle', methods=['POST'])
@login_required
@character_owner_required
def toggle_skill_proficiency(character_id, skill_name):
    """Toggle proficiency on/off for a skill."""
    db = get_db()
    char = db.execute(
        'SELECT data FROM characters WHERE id = ?',
        (character_id,)
    ).fetchone()

    try:
        data = json.loads(char['data'])
        character = Character(data)

        skills = data.get('skills', {})
        if skill_name not in skills:
            return jsonify({'error': f"Unknown skill: {skill_name}"}), 400

        current_proficient, _ = skills[skill_name]
        character.set_skill_proficiency(skill_name, proficient=not current_proficient)

        new_proficient, new_modifier = character.data['skills'][skill_name]

        db.execute(
            'UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(character.data), character_id)
        )
        db.commit()

        return jsonify({
            'success': True,
            'skill': skill_name,
            'proficient': new_proficient,
            'modifier': new_modifier,
            'sign': '+' if new_modifier >= 0 else '',
        })

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error toggling skill proficiency: {e}")
        return jsonify({'error': 'Error updating skill proficiency'}), 500


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

        # Fetch authoritative level data from API
        import random
        level_data = utils._get_class_level_data(data.get('class', ''), new_level)
        data['proficiency_bonus'] = level_data.get('prof_bonus', data.get('proficiency_bonus', 2))
        data['features'] = level_data.get('features', data.get('features', []))
        data['class_specific'] = level_data.get('class_specific', data.get('class_specific', {}))

        # Update spell slots from the new level's spellcasting data and reset used slots
        sc = level_data.get('spellcasting', {})
        data['spell_slots'] = [
            0,
            sc.get('spell_slots_level_1', 0),
            sc.get('spell_slots_level_2', 0),
            sc.get('spell_slots_level_3', 0),
            sc.get('spell_slots_level_4', 0),
            sc.get('spell_slots_level_5', 0),
            sc.get('spell_slots_level_6', 0),
            sc.get('spell_slots_level_7', 0),
            sc.get('spell_slots_level_8', 0),
            sc.get('spell_slots_level_9', 0),
        ]
        data['spell_slots_used'] = [0] * 10

        # Add HP (hit die + CON modifier)
        hit_die = data.get('hit_die', 8)
        con_mod = data['modifiers'][2]
        hp_gain = max(1, random.randint(1, hit_die) + con_mod)
        data['max_hit_points'] += hp_gain
        data['hit_points'] = data['max_hit_points']

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
            'max_hp': data['max_hit_points'],
            'hp_gained': hp_gain,
            'proficiency_bonus': data['proficiency_bonus']
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
        feats = data.get('feats', [])

        class_index = utils._normalize_class_index(data.get('class', ''))
        current_level = data.get('level', 1)

        # Collect and enrich features from every level 1..current, in order.
        features = []
        for lvl in range(1, current_level + 1):
            level_data = get_class_level_data(class_index, lvl) or {}
            for f in level_data.get('features', []):
                detail = get_feature_detail(f['index'])
                desc_paragraphs = detail.get('desc', []) if detail else []
                features.append({
                    **f,
                    'gained_at_level': lvl,
                    'description': '\n\n'.join(desc_paragraphs) if desc_paragraphs else None,
                })
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
    
def _normalize_spell_slots(data: dict) -> tuple:
    """Return (spell_slots, spell_slots_used) as lists of 10 ints, migrating old dict format."""
    slots = data.get('spell_slots', [0] * 10)
    if isinstance(slots, dict):
        slots = [0] + [slots.get(f'level_{i}', 0) for i in range(1, 10)]
    used = data.get('spell_slots_used', [0] * 10)
    return slots, used


@bp.route('/<int:character_id>/spells/list', methods=['GET'])
@login_required
@character_owner_required
def list_spells(character_id):
    """List character spells, slot tracker, and class spell browser."""
    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()

    try:
        data = json.loads(char['data'])
    except json.JSONDecodeError as e:
        logger.error(f"Error loading spells: {e}")
        flash('Error loading character spells', 'error')
        return redirect(url_for('character.view', character_id=character_id))

    spell_slots, spell_slots_used = _normalize_spell_slots(data)
    known_indices = data.get('known_spells', [])

    # Fetch full detail for each known spell (cached)
    known_spells = []
    for idx in known_indices:
        detail = get_spell_detail(idx)
        if detail:
            known_spells.append({
                'index': idx,
                'name': detail.get('name', idx),
                'level': detail.get('level', 0),
                'school': detail.get('school', {}).get('name', ''),
                'casting_time': detail.get('casting_time', ''),
                'range': detail.get('range', ''),
                'duration': detail.get('duration', ''),
                'concentration': detail.get('concentration', False),
                'ritual': detail.get('ritual', False),
                'components': detail.get('components', []),
                'material': detail.get('material', ''),
                'desc': detail.get('desc', []),
                'higher_level': detail.get('higher_level', []),
            })

    # Fetch class spell list for the browser
    class_index = data.get('class', '').lower().replace(' ', '-')
    class_spell_list = []
    for s in get_class_spells(class_index):
        if s['index'] not in known_indices:
            # only include spells at or below character's maximum slot level
            if s['level'] <= max(i for i in range(10) if spell_slots[i] > 0):
                class_spell_list.append({'index': s['index'], 'name': s['name']})

    # Build slot rows — only include levels that have at least one slot
    slot_levels = [
        {'level': i, 'total': spell_slots[i], 'used': spell_slots_used[i]}
        for i in range(1, 10)
        if spell_slots[i] > 0
    ]

    return render_template(
        'character/spells.html',
        character_id=character_id,
        character=data,
        spell_slots=spell_slots,
        slot_levels=slot_levels,
        known_spells=known_spells,
        class_spell_list=class_spell_list,
    )


@bp.route('/<int:character_id>/spells/slot/use/<int:slot_level>', methods=['POST'])
@login_required
@character_owner_required
def use_spell_slot(character_id, slot_level):
    """Mark one spell slot at the given level as used."""
    if not 1 <= slot_level <= 9:
        return jsonify({'error': 'Invalid slot level'}), 400

    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()
    try:
        data = json.loads(char['data'])
        slots, used = _normalize_spell_slots(data)
        if used[slot_level] >= slots[slot_level]:
            return jsonify({'error': 'No slots remaining'}), 400
        used[slot_level] += 1
        data['spell_slots'] = slots
        data['spell_slots_used'] = used
        db.execute('UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
                   (json.dumps(data), character_id))
        db.commit()
        return jsonify({'success': True, 'used': used[slot_level], 'total': slots[slot_level]})
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error using spell slot: {e}")
        return jsonify({'error': 'Server error'}), 500


@bp.route('/<int:character_id>/spells/slot/restore/<int:slot_level>', methods=['POST'])
@login_required
@character_owner_required
def restore_spell_slot(character_id, slot_level):
    """Mark one spell slot at the given level as restored."""
    if not 1 <= slot_level <= 9:
        return jsonify({'error': 'Invalid slot level'}), 400

    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()
    try:
        data = json.loads(char['data'])
        slots, used = _normalize_spell_slots(data)
        if used[slot_level] <= 0:
            return jsonify({'error': 'No used slots to restore'}), 400
        used[slot_level] -= 1
        data['spell_slots'] = slots
        data['spell_slots_used'] = used
        db.execute('UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
                   (json.dumps(data), character_id))
        db.commit()
        return jsonify({'success': True, 'used': used[slot_level], 'total': slots[slot_level]})
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error restoring spell slot: {e}")
        return jsonify({'error': 'Server error'}), 500


@bp.route('/<int:character_id>/spells/slot/reset', methods=['POST'])
@login_required
@character_owner_required
def reset_spell_slots(character_id):
    """Restore all spell slots (long rest)."""
    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()
    try:
        data = json.loads(char['data'])
        slots, _ = _normalize_spell_slots(data)
        data['spell_slots'] = slots
        data['spell_slots_used'] = [0] * 10
        db.execute('UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
                   (json.dumps(data), character_id))
        db.commit()
        return jsonify({'success': True})
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error resetting spell slots: {e}")
        return jsonify({'error': 'Server error'}), 500


@bp.route('/<int:character_id>/spells/add', methods=['POST'])
@login_required
@character_owner_required
def add_spell(character_id):
    """Add a spell to the character's known spells."""
    spell_index = request.form.get('spell_index', '').strip()
    if not spell_index:
        return jsonify({'error': 'Missing spell index'}), 400

    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()
    try:
        data = json.loads(char['data'])
        known = data.get('known_spells', [])
        if spell_index in known:
            return jsonify({'error': 'Spell already known'}), 400
        known.append(spell_index)
        data['known_spells'] = known
        db.execute('UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
                   (json.dumps(data), character_id))
        db.commit()
        detail = get_spell_detail(spell_index)
        spell_name = detail.get('name', spell_index) if detail else spell_index
        return jsonify({'success': True, 'spell': spell_name})
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error adding spell: {e}")
        return jsonify({'error': 'Server error'}), 500


@bp.route('/<int:character_id>/spells/remove/<spell_index>', methods=['POST'])
@login_required
@character_owner_required
def remove_spell(character_id, spell_index):
    """Remove a spell from the character's known spells."""
    db = get_db()
    char = db.execute('SELECT data FROM characters WHERE id = ?', (character_id,)).fetchone()
    try:
        data = json.loads(char['data'])
        known = data.get('known_spells', [])
        if spell_index not in known:
            return jsonify({'error': 'Spell not found'}), 404
        known.remove(spell_index)
        data['known_spells'] = known
        db.execute('UPDATE characters SET data = ?, updated = CURRENT_TIMESTAMP WHERE id = ?',
                   (json.dumps(data), character_id))
        db.commit()
        return jsonify({'success': True})
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error removing spell: {e}")
        return jsonify({'error': 'Server error'}), 500

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
