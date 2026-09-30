import pytest
import sys
import os
import uuid
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.app import app, dialog
from dialog_service.models import UserSession, ConversationHistory
from flask_jwt_extended import create_access_token
from api.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def auth_fixture():
    app.config['TESTING'] = True
    uid_a = f"alice_{uuid.uuid4().hex[:8]}"
    uid_b = f"bob_{uuid.uuid4().hex[:8]}"
    with app.test_client() as client:
        with app.app_context():
            token_a = create_access_token(identity=uid_a)
            token_b = create_access_token(identity=uid_b)
        headers_a = {'Authorization': f'Bearer {token_a}', 'Content-Type': 'application/json'}
        headers_b = {'Authorization': f'Bearer {token_b}', 'Content-Type': 'application/json'}
        yield client, headers_a, headers_b


def test_dashboard_user_isolation(auth_fixture):
    client, headers_a, headers_b = auth_fixture

    # Alice creates 1 session and sends a chat message
    res_a_session = client.post('/session/new', json={'title': "Alice's Chat"}, headers=headers_a)
    session_id_a = res_a_session.json['session_id']
    client.post('/chat', json={'message': "Hello Alice", 'session_id': session_id_a}, headers=headers_a)

    # Bob creates 2 sessions
    res_b_session1 = client.post('/session/new', json={'title': "Bob's Chat 1"}, headers=headers_b)
    session_id_b1 = res_b_session1.json['session_id']
    client.post('/chat', json={'message': "Hello Bob 1", 'session_id': session_id_b1}, headers=headers_b)

    res_b_session2 = client.post('/session/new', json={'title': "Bob's Chat 2"}, headers=headers_b)
    session_id_b2 = res_b_session2.json['session_id']
    client.post('/chat', json={'message': "Hello Bob 2", 'session_id': session_id_b2}, headers=headers_b)

    # Get Alice dashboard stats
    alice_stats = client.get('/api/dashboard/stats', headers=headers_a).json
    # Get Bob dashboard stats
    bob_stats = client.get('/api/dashboard/stats', headers=headers_b).json

    # Alice should only see her own sessions & messages
    assert alice_stats['total_sessions'] == 1
    assert bob_stats['total_sessions'] == 2
    assert alice_stats['total_messages'] == 1
    assert bob_stats['total_messages'] == 2


def test_idor_chat_session_protection(auth_fixture):
    client, headers_a, headers_b = auth_fixture

    # Alice creates a session
    res_a = client.post('/session/new', json={'title': "Alice's Private Session"}, headers=headers_a)
    session_a = res_a.json['session_id']

    # Alice can post to it
    res_alice_chat = client.post('/chat', json={'message': "Secret message from Alice", 'session_id': session_a}, headers=headers_a)
    assert res_alice_chat.status_code == 200

    # Bob attempts to post into Alice's session (IDOR attack)
    res_bob_attack = client.post('/chat', json={'message': "Intrusion from Bob", 'session_id': session_a}, headers=headers_b)
    # Must be forbidden (403)
    assert res_bob_attack.status_code == 403
    assert "Forbidden" in res_bob_attack.json.get('error', '')


def test_sessions_listing_user_isolation(auth_fixture):
    client, headers_a, headers_b = auth_fixture

    # Alice creates a session
    res_a = client.post('/session/new', json={'title': "Alice Only Session"}, headers=headers_a)
    session_a = res_a.json['session_id']

    # Bob lists his sessions
    bob_sessions = client.get('/sessions', headers=headers_b).json['sessions']
    bob_session_ids = [s['session_id'] for s in bob_sessions]

    # Bob must NOT see Alice's session
    assert session_a not in bob_session_ids


def test_rate_limiter_logic():
    limiter = InMemoryRateLimiter()

    # Define mock function decorated with limiter (max 3 per 60s)
    call_count = 0

    @limiter.limit(max_requests=3, window_seconds=60, key_func=lambda: "test_key")
    def sample_endpoint():
        nonlocal call_count
        call_count += 1
        return "success", 200

    with app.test_request_context():
        res1 = sample_endpoint()
        res2 = sample_endpoint()
        res3 = sample_endpoint()
        assert call_count == 3

        # 4th call exceeds limit
        res4, code4 = sample_endpoint()
        assert code4 == 429
        assert "Rate limit exceeded" in res4.json['error']


def test_jwt_access_token_expires_setting():
    from datetime import timedelta
    assert isinstance(app.config['JWT_ACCESS_TOKEN_EXPIRES'], timedelta)
    assert app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds() > 0
