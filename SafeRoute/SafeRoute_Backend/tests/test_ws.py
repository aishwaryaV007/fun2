from fastapi.testclient import TestClient

import main
import api.routes.active_users as active_users
from services.websocket import admin_manager


def _reset_ws_state() -> None:
    admin_manager.active_connections.clear()
    active_users._active_users.clear()
    active_users._user_sockets.clear()


def test_sos_stream_broadcasts_to_multiple_admin_clients() -> None:
    _reset_ws_state()

    with TestClient(main.app, raise_server_exceptions=False) as client:
        with client.websocket_connect("/sos/stream") as admin1, client.websocket_connect("/sos/stream") as admin2:
            response = client.post(
                "/sos/trigger",
                json={
                    "user_id": "ws-test-user",
                    "latitude": 17.43,
                    "longitude": 78.34,
                    "timestamp": "2026-03-15T17:15:00Z",
                    "message": "test websocket broadcast",
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert body["admin_clients_notified"] == 2

            msg1 = admin1.receive_json()
            msg2 = admin2.receive_json()

            assert msg1["type"] == "SOS_ALERT"
            assert msg2["type"] == "SOS_ALERT"
            assert msg1["user_id"] == "ws-test-user"
            assert msg2["user_id"] == "ws-test-user"
            assert msg1["location"] == msg2["location"]

    assert len(admin_manager.active_connections) == 0


def test_ws_users_broadcasts_counts_on_connect_and_disconnect() -> None:
    _reset_ws_state()

    with TestClient(main.app, raise_server_exceptions=False) as client:
        with client.websocket_connect("/sos/stream") as admin:
            with client.websocket_connect("/ws/users") as mobile1:
                connect_msg = admin.receive_json()
                assert connect_msg["type"] == "active_users"
                assert connect_msg["count"] == 1
                assert client.get("/users/count").json()["active_users"] == 1

                mobile1.send_text("ping")

                with client.websocket_connect("/ws/users") as mobile2:
                    connect_msg = admin.receive_json()
                    assert connect_msg["type"] == "active_users"
                    assert connect_msg["count"] == 2
                    assert client.get("/users/count").json()["active_users"] == 2

                    mobile2.send_text("ping")

                disconnect_msg = admin.receive_json()
                assert disconnect_msg["type"] == "active_users"
                assert disconnect_msg["count"] == 1
                assert client.get("/users/count").json()["active_users"] == 1

            disconnect_msg = admin.receive_json()
            assert disconnect_msg["type"] == "active_users"
            assert disconnect_msg["count"] == 0
            assert client.get("/users/count").json()["active_users"] == 0
