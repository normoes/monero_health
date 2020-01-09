import mock
import pytest
import logging
import json

from monerorpc.authproxy import JSONRPCException
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ReadTimeout,
    Timeout,
)

from monero_health import (
    daemon_status_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
)

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_ok(mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }
    
    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["version"] == 12
    assert response["host"] == "127.0.0.1:18081"

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        assert record.message == "Checking '127.0.0.1:18081'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok(mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_ERROR,
        "version": 12,
    }
    caplog.set_level(logging.ERROR, logger="DaemonHealth")
    
    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["version"] == 12
    assert response["host"] == "127.0.0.1:18081"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong error."
    assert response["error"]["message"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_rpc_error(mock_monero_rpc, caplog):
    """Raises a JSONRPCException.

    Source: https://github.com/monero-ecosystem/python-monerorpc/blob/master/monerorpc/authproxy.py
    """

    mock_monero_rpc.side_effect = JSONRPCException(rpc_error={"message": "Some Monero RPC error.", "code": 11})

    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["version"] == -1
    assert response["host"] == "127.0.0.1:18081"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "11: Some Monero RPC error."
    assert response["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "11: Some Monero RPC error.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_read_timeout(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ReadTimeout

    """

    mock_monero_rpc.side_effect = ReadTimeout("Request timed out when reading response.")

    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["version"] == -1
    assert response["host"] == "127.0.0.1:18081"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Request timed out when reading response."
    assert response["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out when reading response.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_connection_error(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ConnectionError

    """

    mock_monero_rpc.side_effect = RequestsConnectionError("Error when connecting.")

    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["version"] == -1
    assert response["host"] == "127.0.0.1:18081"
    
    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Error when connecting."
    assert response["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Error when connecting.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_timeout(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.Timeout

    """

    mock_monero_rpc.side_effect = Timeout("Request timed out.")

    response = daemon_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["version"] == -1
    assert response["host"] == "127.0.0.1:18081"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Request timed out."
    assert response["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out.", "Wrong log message."
    caplog.clear()
