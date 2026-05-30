import pytest
import sys
import os

# Fix path to find api/app.py from tests folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    res = client.get('/')
    assert res.status_code == 200
    assert res.json['status'] == 'ok'
    print("✓ Home endpoint working")

def test_health(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json['status'] == 'healthy'
    print("✓ Health endpoint working")

def test_new_session(client):
    res = client.post('/session/new')
    assert res.status_code == 200
    assert 'session_id' in res.json
    assert len(res.json['session_id']) > 0
    print("✓ Session creation working")

def test_chat_greeting(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "Hello", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert 'bot_response' in res.json
    assert res.json['intent'] == 'greeting'
    print("✓ Greeting intent working")

def test_chat_order_status(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "Where is my order #12345?", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'check_order_status'
    assert res.json['entities']['order_id'] == '12345'
    print("✓ Order status intent working")

def test_chat_cancel_order(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "Cancel my order #67890", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'cancel_order'
    print("✓ Cancel order intent working")

def test_chat_refund(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "I want a refund", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'request_refund'
    print("✓ Refund intent working")

def test_missing_message(client):
    res = client.post('/chat',
        json={},
        content_type='application/json'
    )
    assert res.status_code == 400
    print("✓ Error handling working")

def test_multi_turn_context(client):
    session = client.post('/session/new').json['session_id']
    client.post('/chat',
        json={"message": "Hello", "session_id": session},
        content_type='application/json'
    )
    client.post('/chat',
        json={"message": "Where is order #12345?", "session_id": session},
        content_type='application/json'
    )
    history = client.get(f'/history/{session}')
    assert len(history.json['history']) == 2
    print("✓ Multi-turn conversation working")

def test_dialog_fsm_slot_filling(client):
    # 1. Create session
    session = client.post('/session/new').json['session_id']
    
    # 2. Trigger check order status without providing the order ID
    res1 = client.post('/chat',
        json={"message": "Where is my order?", "session_id": session},
        content_type='application/json'
    )
    assert res1.status_code == 200
    assert "provide your order number" in res1.json['bot_response']
    assert res1.json['engine'] == 'support_engine'
    
    # 3. Supply the order ID on the next turn
    res2 = client.post('/chat',
        json={"message": "12345", "session_id": session},
        content_type='application/json'
    )
    assert res2.status_code == 200
    # Auto-routing should have executed and returned actual database status for #12345!
    assert "Shipped" in res2.json['bot_response']
    assert "Tomorrow by 8 PM" in res2.json['bot_response']
    assert res2.json['engine'] == 'support_engine'
    print("✓ FSM Dialog Slot-filling working perfectly")