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
    daemon_last_block_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
)

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_recent(mock_time_range, mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.get_last_block_header.return_value = {
        "block_header": {
            "timestamp": "1576828533",
            "hash": "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a",
        },
    }
    mock_time_range.return_value = (True, 12, "minutes")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["block_recent"] == True
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"
    assert response["hash"] == "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a"

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        assert record.message == "Checking '127.0.0.1:18081'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_not_recent_timestamp_old(mock_time_range, mock_monero_rpc, caplog):
    mock_monero_rpc.return_value.get_last_block_header.return_value = {
        "block_header": {
            "timestamp": "1576828533",
            "hash": "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a",
        },
    }
    mock_time_range.return_value = (False, 12, "minutes")
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["block_recent"] == False
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Last block's timestamp is '12 [minutes]' old.", "Wrong error."
    assert response["error"]["message"] == "Last block's timestamp is '12 [minutes]' old. Daemon: '127.0.0.1:18081'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Last block's timestamp is '12 [minutes]' old. Daemon: '127.0.0.1:18081'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_not_recent_rpc_error(mock_time_range, mock_monero_rpc, caplog):
    """Raises a JSONRPCException.

    Source: https://github.com/monero-ecosystem/python-monerorpc/blob/master/monerorpc/authproxy.py
    """

    mock_monero_rpc.side_effect = JSONRPCException(rpc_error={"message": "Some Monero RPC error.", "code": 11})
    mock_time_range.return_value = (True, 12, "minutes")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["block_recent"] == False
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "11: Some Monero RPC error."
    assert response["error"]["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "11: Some Monero RPC error.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_not_recent_read_timeout(mock_time_range, mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ReadTimeout

    """

    mock_monero_rpc.side_effect = ReadTimeout("Request timed out when reading response.")
    mock_time_range.return_value = (True, 12, "minutes")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["block_recent"] == False
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Request timed out when reading response."
    assert response["error"]["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out when reading response.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_not_recent_connection_error(mock_time_range, mock_monero_rpc, caplog):
    """Raises a requests.exceptions.ConnectionError

    """

    mock_monero_rpc.side_effect = RequestsConnectionError("Error when connecting.")
    mock_time_range.return_value = (True, 12, "minutes")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["block_recent"] == False
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Error when connecting."
    assert response["error"]["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Error when connecting.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
def test_last_block_not_recent_timeout(mock_time_range, mock_monero_rpc, caplog):
    """Raises a requests.exceptions.Timeout

    """

    mock_monero_rpc.side_effect = Timeout("Request timed out.")
    mock_time_range.return_value = (True, 12, "minutes")

    response = daemon_last_block_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["block_recent"] == False
    assert response["block_recent_offset"] == 12
    assert response["block_recent_offset_unit"] == "minutes"

    assert "error" in response
    assert "error" in response["error"]
    assert "message" in response["error"]
    assert response["error"]["error"] == "Request timed out."
    assert response["error"]["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine daemon status. Daemon: '127.0.0.1:18081'.", "Wrong log message."
        assert "error" in json_message, "Wrong log message."
        assert json_message["error"] == "Request timed out.", "Wrong log message."
    caplog.clear()
