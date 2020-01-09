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
    daemon_combined_status_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
    HEALTH_KEY,
    LAST_BLOCK_KEY,
    DAEMON_KEY,
)

@mock.patch("monero_health.daemon_status_check")
@mock.patch("monero_health.daemon_last_block_check")
def test_combined_status_ok(mock_last_block, mock_daemon, caplog):
    last_block_result = {
        "block_recent": True,
        "block_recent_offset": 12,
        "block_recent_offset_unit": "minutes",
        "block_timestamp": "2020-01-07T12:22:31",
        "check_timestamp": "2020-01-07T12:29:27",
        "hash": "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160",
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18081",
    }
    mock_last_block.return_value = last_block_result
    daemon_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon.return_value = daemon_result
    
    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1:18081"

    assert LAST_BLOCK_KEY in response
    assert not "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"] == True
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert response[LAST_BLOCK_KEY]["hash"] == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    assert DAEMON_KEY in response
    assert not "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == f"Combined status is '{DAEMON_STATUS_OK}'."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
@mock.patch("monero_health.daemon_status_check")
def test_combined_status_old_last_block(mock_daemon, mock_time_range, mock_monero_rpc, caplog):
    """Check combined daemon status.

    Last block status is 'ERROR' due to old last block.
    Daemon status itself is fine.
    """

    mock_monero_rpc.return_value.get_last_block_header.return_value = {
        "block_header": {
            "timestamp": "1576828533",
            "hash": "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a",
        },
    }
    mock_time_range.return_value = (False, 12, "minutes")

    daemon_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon.return_value = daemon_result
    
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1:18081"

    assert LAST_BLOCK_KEY in response
    assert not "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_ERROR
    assert response[LAST_BLOCK_KEY]["block_recent"] == False
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2019-12-20T07:55:33"
    assert response[LAST_BLOCK_KEY]["hash"] == "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a"
    assert DAEMON_KEY in response
    assert not "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12

    assert "error" in response[LAST_BLOCK_KEY]
    assert "error" in response[LAST_BLOCK_KEY]["error"]
    assert "message" in response[LAST_BLOCK_KEY]["error"]
    assert response[LAST_BLOCK_KEY]["error"]["error"] == "Last block's timestamp is older than '12 [minutes]'.", "Wrong error."
    assert response[LAST_BLOCK_KEY]["error"]["message"] == "Last block's timestamp is older than '12 [minutes]'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Last block's timestamp is older than '12 [minutes]'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.daemon_last_block_check")
def test_combined_status_daemon_status_error(mock_last_block, mock_monero_rpc, caplog):
    """Check combined daemon status.

    Daemon status is 'ERROR' due to result of Moenro RPC 'hard_fork_info'.
    Last block status is fine.
    """

    last_block_result = {
        "block_recent": True,
        "block_recent_offset": 12,
        "block_recent_offset_unit": "minutes",
        "block_timestamp": "2020-01-07T12:22:31",
        "check_timestamp": "2020-01-07T12:29:27",
        "hash": "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160",
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18081",
    }
    mock_last_block.return_value = last_block_result

    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_ERROR,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1:18081"

    assert LAST_BLOCK_KEY in response
    assert not "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"] == True
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert response[LAST_BLOCK_KEY]["hash"] == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    assert DAEMON_KEY in response
    assert not "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_ERROR
    assert response[DAEMON_KEY]["version"] == 12

    assert "error" in response[DAEMON_KEY]
    assert "error" in response[DAEMON_KEY]["error"]
    assert "message" in response[DAEMON_KEY]["error"]
    assert response[DAEMON_KEY]["error"]["error"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong error."
    assert response[DAEMON_KEY]["error"]["message"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == f"Status is '{DAEMON_STATUS_ERROR}'.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.is_timestamp_within_offset")
@mock.patch("monero_health.daemon_status_check")
def test_combined_status_unknown_last_block_status(mock_daemon, mock_time_range, mock_monero_rpc, caplog):
    """Check combined daemon status.

    Last block tstaus is unknown due to request timeout.
    Daemon status itself is fine.
    """

    mock_monero_rpc.side_effect = JSONRPCException(rpc_error={"message": "Some Monero RPC error.", "code": 11})
    mock_time_range.return_value = (True, 12, "minutes")

    daemon_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon.return_value = daemon_result
    
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1:18081"

    assert LAST_BLOCK_KEY in response
    assert not "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert response[LAST_BLOCK_KEY]["block_recent"] == False
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "---"
    assert response[LAST_BLOCK_KEY]["hash"] == "---"
    assert DAEMON_KEY in response
    assert not "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12

    assert "error" in response[LAST_BLOCK_KEY]
    assert "error" in response[LAST_BLOCK_KEY]["error"]
    assert "message" in response[LAST_BLOCK_KEY]["error"]
    assert response[LAST_BLOCK_KEY]["error"]["error"] == "11: Some Monero RPC error.", "Wrong error."
    assert response[LAST_BLOCK_KEY]["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
    caplog.clear()

@mock.patch("monero_health.AuthServiceProxy")
@mock.patch("monero_health.daemon_last_block_check")
def test_combined_status_unknown_daemon_status(mock_last_block, mock_monero_rpc, caplog):
    """Check combined daemon status.

    Daemon status is 'UNKNOWN' due to Moenro RPC error.
    Last block status is fine.
    """

    last_block_result = {
        "block_recent": True,
        "block_recent_offset": 12,
        "block_recent_offset_unit": "minutes",
        "block_timestamp": "2020-01-07T12:22:31",
        "check_timestamp": "2020-01-07T12:29:27",
        "hash": "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160",
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18081",
    }
    mock_last_block.return_value = last_block_result
    mock_monero_rpc.side_effect = JSONRPCException(rpc_error={"message": "Some Monero RPC error.", "code": 11})
    
    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1:18081"

    assert LAST_BLOCK_KEY in response
    assert not "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"] == True
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert response[LAST_BLOCK_KEY]["hash"] == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    assert DAEMON_KEY in response
    assert not "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert response[DAEMON_KEY]["version"] == -1

    assert "error" in response[DAEMON_KEY]
    assert "error" in response[DAEMON_KEY]["error"]
    assert "message" in response[DAEMON_KEY]["error"]
    assert response[DAEMON_KEY]["error"]["error"] == "11: Some Monero RPC error.", "Wrong error."
    assert response[DAEMON_KEY]["error"]["message"] == "Cannot determine status.", "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert json_message["message"] == "Cannot determine status.", "Wrong log message."
    caplog.clear()
