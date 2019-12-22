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
)

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_ok(mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": "OK",
        "version": "12",
    }
    
    response = daemon_status_check()

    assert response["status"] == "OK"
    assert response["version"] == "12"

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        assert record.message == "Checking '127.0.0.1:18081'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok(mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": "ERROR",
        "version": "12",
    }
    caplog.set_level(logging.ERROR, logger="DaemonHealth")
    
    response = daemon_status_check()

    assert response["status"] == "ERROR"
    assert response["version"] == "12"

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert not "error" in json_message, "Wrong log message."
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Dameon status is 'ERROR'. Daemon: '127.0.0.1:18081'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_rpc_error(mock_monero_rpc, caplog):
    """Raises a JSONRPCException.

    Source: https://github.com/monero-ecosystem/python-monerorpc/blob/master/monerorpc/authproxy.py
    """

    mock_monero_rpc.side_effect = JSONRPCException(rpc_error={"message": "Some Monero RPC error.", "code": 11})

    response = daemon_status_check()

    assert response["status"] == "ERROR"
    assert response["error"] == "11: Some Monero RPC error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Dameon status is 'ERROR'. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "11: Some Monero RPC error.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_read_timeout(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ReadTimeout

    """

    mock_monero_rpc.side_effect = ReadTimeout("Request timed out when reading response.")

    response = daemon_status_check()

    assert response["status"] == "ERROR"
    assert response["error"] == "Request timed out when reading response."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Dameon status is 'ERROR'. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out when reading response.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_connection_error(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ConnectionError

    """

    mock_monero_rpc.side_effect = RequestsConnectionError("Error when connecting.")

    response = daemon_status_check()

    assert response["status"] == "ERROR"
    assert response["error"] == "Error when connecting."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Dameon status is 'ERROR'. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Error when connecting.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
def test_daemon_status_not_ok_timeout(mock_monero_rpc, caplog):
    """Raises a requests.exceptions.Timeout

    """

    mock_monero_rpc.side_effect = Timeout("Request timed out.")

    response = daemon_status_check()

    assert response["status"] == "ERROR"
    assert response["error"] == "Request timed out."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Dameon status is 'ERROR'. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out.", "Wrong log message."
    caplog.clear()
