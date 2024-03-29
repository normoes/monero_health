import mock
import logging
import json
import socket

from monerorpc.authproxy import JSONRPCException

from monero_health.monero_health import (
    daemon_combined_status_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
    # HEALTH_KEY,
    LAST_BLOCK_KEY,
    DAEMON_KEY,
    DAEMON_P2P_KEY,
    DAEMON_RPC_KEY,
)


@mock.patch("monero_health.monero_health.daemon_stati_check")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
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
        "block_age": "0:00:19",
    }
    mock_last_block.return_value = last_block_result
    # Add 'noqa' comment to make flake8 ignore E231 missing whitespace after ','
    daemon_result = {
        DAEMON_RPC_KEY: {
            "status": DAEMON_STATUS_OK,
            "host": "127.0.0.1:18081",
        },
        DAEMON_P2P_KEY: {
            "status": DAEMON_STATUS_OK,
            "host": "127.0.0.1:18080",  # noqa: E231
        },
        "host": "127.0.0.1",
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }
    mock_daemon.return_value = daemon_result

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert "block_age" in response[LAST_BLOCK_KEY]
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined status is '{DAEMON_STATUS_OK}'."
        )
    caplog.clear()


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.is_timestamp_within_offset")
@mock.patch("monero_health.monero_health.daemon_rpc_status_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_old_last_block(
    mock_socket, mock_daemon, mock_time_range, mock_monero_rpc, caplog
):
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

    response = daemon_combined_status_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_ERROR
    assert not response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2019-12-20T07:55:33"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3f82c93e6f7726a54724d0b8b1026bec878af449bc2f97e9a916c6af72a6367a"
    )
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[LAST_BLOCK_KEY]
    assert "error" in response[LAST_BLOCK_KEY]["error"]
    assert "message" in response[LAST_BLOCK_KEY]["error"]
    assert response[LAST_BLOCK_KEY]["error"]["error"].startswith(
        "Last block's age is '"
    ), "Wrong error."
    assert (
        response[LAST_BLOCK_KEY]["error"]["message"]
        == "Last block's timestamp is older than '12 [minutes]'."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == "Last block's timestamp is older than '12 [minutes]'."
        ), "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_daemon_rpc_status_error(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon RPC status is 'ERROR' due to result of Moenro RPC 'hard_fork_info'.
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
        "block_age": "0:00:19",
    }
    mock_last_block.return_value = last_block_result

    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_ERROR,
        "version": 12,
    }

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert "block_age" in response[LAST_BLOCK_KEY]
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_ERROR
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_ERROR
    )
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]["error"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
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


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_daemon_p2p_status_ignore_error(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon P2P status is 'ERROR' due to a connection error by the peer, but the P2P status is ignored in the resultng daemon status.
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
        "block_age": "0:00:19",
    }
    mock_last_block.return_value = last_block_result

    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }

    mock_socket.side_effect = ConnectionError("Something went wrong.")

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert "block_age" in response[LAST_BLOCK_KEY]
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_ERROR
    )

    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["error"]
        == "Something went wrong."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
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


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_daemon_p2p_status_error(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon P2P status is 'ERROR' due to a connection error by the peer.
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
        "block_age": "0:00:19",
    }
    mock_last_block.return_value = last_block_result

    mock_monero_rpc.return_value.hard_fork_info.return_value = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }

    mock_socket.side_effect = ConnectionError("Something went wrong.")

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert "block_age" in response[LAST_BLOCK_KEY]
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_ERROR
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_ERROR
    )

    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["error"]
        == "Something went wrong."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
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


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.is_timestamp_within_offset")
@mock.patch("monero_health.monero_health.daemon_rpc_status_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_unknown_last_block_status(
    mock_socket, mock_daemon, mock_time_range, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Last block tstaus is unknown due to request timeout.
    Daemon status itself is fine.
    """

    mock_monero_rpc.side_effect = JSONRPCException(
        rpc_error={"message": "Some Monero RPC error.", "code": 11}
    )
    mock_time_range.return_value = (True, 12, "minutes")

    daemon_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon.return_value = daemon_result

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check(
        consider_p2p=True,
    )

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert not response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "---"
    assert response[LAST_BLOCK_KEY]["hash"] == "---"
    assert response[LAST_BLOCK_KEY]["block_age"] == -1
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[LAST_BLOCK_KEY]
    assert "error" in response[LAST_BLOCK_KEY]["error"]
    assert "message" in response[LAST_BLOCK_KEY]["error"]
    assert (
        response[LAST_BLOCK_KEY]["error"]["error"]
        == "11: Some Monero RPC error."
    ), "Wrong error."
    assert (
        response[LAST_BLOCK_KEY]["error"]["message"]
        == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == "Cannot determine status."
        ), "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_unknown_daemon_rpc_status(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon RPC status is 'UNKNOWN' due to Moenro RPC error.
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
    mock_monero_rpc.side_effect = JSONRPCException(
        rpc_error={"message": "Some Monero RPC error.", "code": 11}
    )

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check(
        consider_p2p=True,
    )

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert response[DAEMON_KEY]["version"] == -1
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    )
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]["error"]
        == "11: Some Monero RPC error."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_RPC_KEY]["error"]["message"]
        == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == "Cannot determine status."
        ), "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_ignore_unknown_daemon_p2p_status(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon P2P status is 'UNKNOWN' due to a connectivity error.
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
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }

    mock_socket.side_effect = socket.gaierror("Something went wrong.")

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    )

    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["error"]
        == "Something went wrong."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["message"]
        == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == "Cannot determine status."
        ), "Wrong log message."
    caplog.clear()


@mock.patch("monero_health.monero_health.AuthServiceProxy")
@mock.patch("monero_health.monero_health.daemon_last_block_check")
@mock.patch(
    "monero_health.monero_health.connect_to_node.try_to_connect_keep_errors"
)
def test_combined_status_unknown_daemon_p2p_status(
    mock_socket, mock_last_block, mock_monero_rpc, caplog
):
    """Check combined daemon status.

    Daemon P2P status is 'UNKNOWN' due to a connectivity error.
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
        "status": DAEMON_STATUS_OK,
        "version": 12,
    }

    mock_socket.side_effect = socket.gaierror("Something went wrong.")

    caplog.set_level(logging.ERROR, logger="DaemonHealth")

    response = daemon_combined_status_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1"

    assert LAST_BLOCK_KEY in response
    assert "host" in response[LAST_BLOCK_KEY]
    assert response[LAST_BLOCK_KEY]["host"] == "127.0.0.1:18081"
    assert response[LAST_BLOCK_KEY]["status"] == DAEMON_STATUS_OK
    assert response[LAST_BLOCK_KEY]["block_recent"]
    assert response[LAST_BLOCK_KEY]["block_recent_offset"] == 12
    assert response[LAST_BLOCK_KEY]["block_recent_offset_unit"] == "minutes"
    assert response[LAST_BLOCK_KEY]["block_timestamp"] == "2020-01-07T12:22:31"
    assert (
        response[LAST_BLOCK_KEY]["hash"]
        == "3321dcedc99ff78c56e06d5adcb79c25e587df76a35f13771f20d6c9551cf160"
    )
    assert DAEMON_KEY in response
    assert "host" in response[DAEMON_KEY]
    assert response[DAEMON_KEY]["host"] == "127.0.0.1"
    assert response[DAEMON_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert response[DAEMON_KEY]["version"] == 12
    assert DAEMON_RPC_KEY in response[DAEMON_KEY]
    assert DAEMON_P2P_KEY in response[DAEMON_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_KEY][DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert "version" not in response[DAEMON_KEY][DAEMON_RPC_KEY]
    assert "host" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert response[DAEMON_KEY][DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    )

    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["error"]
        == "Something went wrong."
    ), "Wrong error."
    assert (
        response[DAEMON_KEY][DAEMON_P2P_KEY]["error"]["message"]
        == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "ERROR", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"] == "Cannot determine status."
        ), "Wrong log message."
    caplog.clear()
