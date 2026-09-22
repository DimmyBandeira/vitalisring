"""Interface autenticada do simulador sintético."""

from fastapi.testclient import TestClient

import api
from models import SessionLocal, init_db, utcnow_naive
from webapp.models_app import User
from webapp.security.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, create_session


def test_simulator_is_explicit_and_preview_omits_health_values():
    init_db()
    db = SessionLocal()
    user = User(email=f"sim-{utcnow_naive().timestamp()}@example.test", full_name="Dra. Simulação", role="doctor", is_demo=True)
    db.add(user)
    db.commit()
    session = create_session(db, user)
    db.close()
    with TestClient(api.app) as client:
        client.cookies.set(COOKIE_NAME, session.token)
        client.cookies.set(CSRF_COOKIE_NAME, session.csrf_token)
        page = client.get("/app/simulador")
        assert "Somente dados fictícios" in page.text
        assert "limiares ainda não validados" in page.text
        response = client.post(
            "/app/simulador",
            data={"csrf_token": session.csrf_token, "patient_name": "Maria", "state": "rest", "bpm": "130", "spo2": "88", "movement": "low", "duration_seconds": "60", "signal_quality": "0.95"},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200
        assert "Duas estimativas sintéticas" in response.text
        assert "Maria: precisa de você agora" in response.text
        assert "130" not in response.text and "88" not in response.text
