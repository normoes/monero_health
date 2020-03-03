import mock
import logging
import json
import socket

from monero_health import (
    daemon_p2p_status_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
)


@mock.patch("monero_health.connect_to_node.try_to_connect_keep_errors")
def test_daemon_p2p_status_ok(mock_socket, caplog):

    response = daemon_p2p_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1:18080"

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        assert record.message == "Checking '127.0.0.1:18080'.", "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.connect_to_node.try_to_connect_keep_errors")
def test_daemon_status_peer_error(mock_socket, caplog):
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    mock_socket.side_effect = ConnectionError("Something went wrong.")

    response = daemon_p2p_status_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1:18080"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == f"Something went wrong.", "Wrong error."
    assert (
        response["error"]["message"] == f"Status is '{DAEMON_STATUS_ERROR}'."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == f"Status is '{DAEMON_STATUS_ERROR}'."
        ), "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.connect_to_node.try_to_connect_keep_errors")
def test_daemon_status_connectivity_error(mock_socket, caplog):
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    mock_socket.side_effect = socket.gaierror("Something went wrong.")

    response = daemon_p2p_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1:18080"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == f"Something went wrong.", "Wrong error."
    assert response["error"]["message"] == f"Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == f"Cannot determine status."
        ), "Wrong log message."
    caplog.clear()
