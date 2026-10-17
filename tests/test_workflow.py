import os
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient

# The database path must be set before importing the app module.
os.environ['CAREPILOT_DB'] = tempfile.mktemp(suffix='.db')
from app import main

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DB_PATH', tmp_path / 'test.db')
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client

def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_chat_booking_persists_pending_appointment(client):
    response = client.post('/api/chat', json={
        'message': "I'd like to book an appointment tomorrow at 10 am. My name is Priya Shah and I'm visiting for a routine consultation.",
        'session_id': 'test-booking'
    })
    assert response.status_code == 200
    body = response.json()
    assert body['intent'] == 'booking'
    assert body['appointment']['patient_name'] == 'Priya Shah'
    assert body['appointment']['status'] == 'Pending'
    dashboard = client.get('/api/dashboard').json()
    assert any(a['id'] == body['appointment']['id'] for a in dashboard['appointments'])

def test_staff_can_update_appointment_status(client):
    created = client.post('/api/appointments', json={
        'patient_name': 'Demo Patient', 'preferred_time': 'Friday at 11 am', 'reason': 'Routine consultation'
    }).json()['appointment']
    response = client.patch(f"/api/appointments/{created['id']}", json={'status':'Confirmed'})
    assert response.status_code == 200
    assert response.json()['appointment']['status'] == 'Confirmed'

def test_faq_is_sent_to_human_review(client):
    response = client.post('/api/chat', json={'message':'What are your clinic hours?', 'session_id':'test-faq'})
    assert response.status_code == 200
    assert response.json()['needs_staff_review'] is True
    dashboard = client.get('/api/dashboard').json()
    assert any(i['message'] == 'What are your clinic hours?' and i['status'] == 'Needs review' for i in dashboard['inquiries'])

def test_urgent_message_gets_escalation_not_diagnosis(client):
    response = client.post('/api/chat', json={'message':'I am having chest pain', 'session_id':'test-urgent'})
    assert response.status_code == 200
    body = response.json()
    assert body['urgent'] is True
    assert body['needs_staff_review'] is True
    assert 'emergency' in body['reply'].lower()


def test_urgent_escalation_bypasses_external_ai(monkeypatch):
    import asyncio
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    class ExternalClientMustNotBeCalled:
        def __init__(self, *args, **kwargs):
            raise AssertionError('External AI must not be called for urgent escalation')

    monkeypatch.setattr(main.httpx, 'AsyncClient', ExternalClientMustNotBeCalled)
    reply, provider = asyncio.run(main.ai_draft('I am having chest pain', 'urgent_escalation'))
    assert provider == 'Local safety fallback'
    assert 'emergency' in reply.lower()
    assert 'diagnos' not in reply.lower()


def test_staff_can_reschedule_appointment(client):
    created = client.post('/api/appointments', json={
        'patient_name': 'Demo Patient',
        'preferred_time': 'October 20, 2026 at 10:00 AM',
        'reason': 'Routine consultation'
    }).json()['appointment']

    response = client.patch(
        f"/api/appointments/{created['id']}/reschedule",
        json={'preferred_time': 'October 22, 2026 at 11:30 AM'}
    )

    assert response.status_code == 200
    assert response.json()['appointment']['preferred_time'] == (
        'October 22, 2026 at 11:30 AM'
    )
