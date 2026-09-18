"""
Auth Routes — Real JWT-based authentication with bcrypt password hashing.
Endpoints:
  POST /auth/register  — create account
  POST /auth/login     — get JWT token
  GET  /auth/me        — get current user (token required)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from dialog_service.models import User
from dialog_service.state_manager import ConversationState

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Re-use the same DB session as the rest of the app
_state = ConversationState()

def get_db():
    return _state.Session()


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    email = (data.get('email') or '').strip() or None

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    _state._ensure_initialized()
    db = get_db()
    try:
        # Check if username already exists
        existing = db.query(User).filter_by(username=username).first()
        if existing:
            return jsonify({'error': 'Username already taken. Please choose another.'}), 409

        user = User(username=username, email=email)
        user.set_password(password)
        db.add(user)
        db.commit()

        access_token = create_access_token(identity=username)
        return jsonify({
            'message': 'Account created successfully!',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    finally:
        db.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    _state._ensure_initialized()
    db = get_db()
    try:
        user = db.query(User).filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password.'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is disabled.'}), 403

        access_token = create_access_token(identity=username)
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500
    finally:
        db.close()


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    username = get_jwt_identity()
    db = get_db()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found.'}), 404
        return jsonify({'user': user.to_dict()}), 200
    finally:
        db.close()
