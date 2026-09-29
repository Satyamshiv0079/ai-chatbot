import pytest
import sys
import os

# Fix path to find api/app.py from tests folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.app import app
from flask_jwt_extended import create_access_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            token = create_access_token(identity="testuser")
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        yield client

@pytest.fixture
def unauth_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    res = client.get('/')
    assert res.status_code == 200
    assert res.json['status'] == 'ok'

def test_health(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json['status'] == 'healthy'

def test_unauthorized_access(unauth_client):
    """Ensures protected endpoints reject unauthenticated requests."""
    res = unauth_client.post('/session/new')
    assert res.status_code == 401
    res_chat = unauth_client.post('/chat', json={"message": "hello"})
    assert res_chat.status_code == 401

def test_new_session(client):
    res = client.post('/session/new', json={})
    assert res.status_code == 200
    assert 'session_id' in res.json
    assert len(res.json['session_id']) > 0

def test_chat_greeting(client):
    session = client.post('/session/new', json={}).json['session_id']
    res = client.post('/chat',
        json={"message": "Hello", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert 'bot_response' in res.json
    assert res.json['intent'] == 'greeting'

def test_chat_order_status(client):
    session = client.post('/session/new', json={}).json['session_id']
    res = client.post('/chat',
        json={"message": "Where is my order #12345?", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'check_order_status'
    assert res.json['entities']['order_id'] == '12345'

def test_chat_cancel_order(client):
    session = client.post('/session/new', json={}).json['session_id']
    res = client.post('/chat',
        json={"message": "Cancel my order #67890", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'cancel_order'

def test_chat_refund(client):
    session = client.post('/session/new', json={}).json['session_id']
    res = client.post('/chat',
        json={"message": "I want a refund", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'request_refund'

def test_missing_message(client):
    res = client.post('/chat',
        json={},
        content_type='application/json'
    )
    assert res.status_code == 400

def test_multi_turn_context(client):
    session = client.post('/session/new', json={}).json['session_id']
    client.post('/chat',
        json={"message": "Hello", "session_id": session},
        content_type='application/json'
    )
    client.post('/chat',
        json={"message": "Where is order #12345?", "session_id": session},
        content_type='application/json'
    )
    history = client.get(f'/sessions/{session}')
    assert history.status_code == 200
    assert len(history.json['messages']) >= 2