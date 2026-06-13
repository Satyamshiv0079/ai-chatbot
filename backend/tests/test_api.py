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
    assert "Tomorrow by 8 PM" in res2.json['bot_response']
    assert res2.json['engine'] == 'support_engine'
    print("✓ FSM Dialog Slot-filling working perfectly")

def test_chat_goodbye(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "Goodbye", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'goodbye'
    assert 'goodbye' in res.json['bot_response'].lower() or 'day' in res.json['bot_response'].lower()

def test_chat_shipping_info(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "How long does shipping take?", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'shipping_info'
    assert 'shipping' in res.json['bot_response'].lower()

def test_chat_return_policy(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "What is your return policy?", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'return_policy'
    assert 'return' in res.json['bot_response'].lower()

def test_chat_complaint(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "I want to speak to a manager", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'complaint'
    assert 'escalat' in res.json['bot_response'].lower() or 'apologize' in res.json['bot_response'].lower()

def test_chat_thank_you(client):
    session = client.post('/session/new').json['session_id']
    res = client.post('/chat',
        json={"message": "Thanks for your help", "session_id": session},
        content_type='application/json'
    )
    assert res.status_code == 200
    assert res.json['intent'] == 'thank_you'
    assert 'welcome' in res.json['bot_response'].lower() or 'glad' in res.json['bot_response'].lower()

def test_delete_session(client):
    session = client.post('/session/new').json['session_id']
    res_hist = client.get(f'/history/{session}')
    assert res_hist.status_code == 200
    
    res_del = client.delete(f'/session/{session}')
    assert res_del.status_code == 200
    assert res_del.json['success'] is True
    
    res_hist_after = client.get(f'/history/{session}')
    assert res_hist_after.status_code == 404

def test_clear_all_sessions(client):
    session1 = client.post('/session/new').json['session_id']
    session2 = client.post('/session/new').json['session_id']
    
    res_clear = client.delete('/sessions/all')
    assert res_clear.status_code == 200
    assert res_clear.json['success'] is True
    
    assert client.get(f'/history/{session1}').status_code == 404
    assert client.get(f'/history/{session2}').status_code == 404

def test_admin_stats(client):
    session = client.post('/session/new').json['session_id']
    client.post('/chat',
        json={"message": "Hello", "session_id": session},
        content_type='application/json'
    )
    
    res = client.get('/admin/stats')
    assert res.status_code == 200
    data = res.json
    assert 'total_sessions' in data
    assert 'total_messages' in data
    assert 'intent_distribution' in data
    assert 'order_status_breakdown' in data
    assert data['total_sessions'] >= 1
    assert data['total_messages'] >= 1

def test_admin_orders(client):
    res = client.get('/admin/orders')
    assert res.status_code == 200
    assert 'orders' in res.json
    assert len(res.json['orders']) >= 3

def test_update_order_status(client):
    res1 = client.get('/admin/orders')
    assert res1.status_code == 200
    orders = res1.json['orders']
    original_status = next(o['status'] for o in orders if o['order_id'] == '12345')
    
    res2 = client.post('/admin/order/12345/status',
        json={"status": "In Transit"},
        content_type='application/json'
    )
    assert res2.status_code == 200
    assert res2.json['success'] is True
    
    res3 = client.get('/admin/orders')
    updated_status = next(o['status'] for o in res3.json['orders'] if o['order_id'] == '12345')
    assert updated_status == "In Transit"
    
    client.post('/admin/order/12345/status',
        json={"status": original_status},
        content_type='application/json'
    )