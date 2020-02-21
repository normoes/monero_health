import mock
import logging
import json

from monero_health import (
    daemon_stati_check,
    DAEMON_STATUS_OK,
    DAEMON_STATUS_ERROR,
    DAEMON_STATUS_UNKNOWN,
    DAEMON_P2P_KEY,
    DAEMON_RPC_KEY,
)


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_ok(mock_daemon_p2p_status, mock_daemon_rpc_status, caplog):
    rpc_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18080",
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_OK}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_rpc_error(mock_daemon_p2p_status, mock_daemon_rpc_status, caplog):
    caplog.set_level(logging.INFO, logger="DaemonHealth")
    rpc_result = {
        "status": DAEMON_STATUS_ERROR,
        "version": 12,
        "host": "127.0.0.1:18081",
        "error": {
            "error": "Some error.",
            "message": f"Status is '{DAEMON_STATUS_ERROR}'.",
        },
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18080",
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check()

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_ERROR
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[DAEMON_RPC_KEY]
    assert "error" in response[DAEMON_RPC_KEY]["error"]
    assert "message" in response[DAEMON_RPC_KEY]["error"]
    assert response[DAEMON_RPC_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_RPC_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_ERROR}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_rpc_unknown(
    mock_daemon_p2p_status, mock_daemon_rpc_status, caplog
):
    rpc_result = {
        "status": DAEMON_STATUS_UNKNOWN,
        "version": -1,
        "host": "127.0.0.1:18081",
        "error": {"error": "Some error.", "message": "Cannot determine status."},
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_OK,
        "host": "127.0.0.1:18080",
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check()

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_UNKNOWN
    assert response[DAEMON_RPC_KEY]["version"] == -1
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_OK

    assert "error" in response[DAEMON_RPC_KEY]
    assert "error" in response[DAEMON_RPC_KEY]["error"]
    assert "message" in response[DAEMON_RPC_KEY]["error"]
    assert response[DAEMON_RPC_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_RPC_KEY]["error"]["message"] == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_UNKNOWN}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_ignore_p2p_error(
    mock_daemon_p2p_status, mock_daemon_rpc_status, caplog
):
    caplog.set_level(logging.INFO, logger="DaemonHealth")
    rpc_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_ERROR,
        "host": "127.0.0.1:18080",
        "error": {
            "error": "Some error.",
            "message": f"Status is '{DAEMON_STATUS_ERROR}'.",
        },
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_ERROR

    assert "error" in response[DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_P2P_KEY]["error"]
    assert response[DAEMON_P2P_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_P2P_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_OK}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_p2p_error(mock_daemon_p2p_status, mock_daemon_rpc_status, caplog):
    caplog.set_level(logging.INFO, logger="DaemonHealth")
    rpc_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_ERROR,
        "host": "127.0.0.1:18080",
        "error": {
            "error": "Some error.",
            "message": f"Status is '{DAEMON_STATUS_ERROR}'.",
        },
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_ERROR
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_ERROR

    assert "error" in response[DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_P2P_KEY]["error"]
    assert response[DAEMON_P2P_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_P2P_KEY]["error"]["message"]
        == f"Status is '{DAEMON_STATUS_ERROR}'."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_ERROR}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_ignore_p2p_unknown(
    mock_daemon_p2p_status, mock_daemon_rpc_status, caplog
):
    rpc_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_UNKNOWN,
        "host": "127.0.0.1:18080",
        "error": {"error": "Some error.", "message": "Cannot determine status."},
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check()

    assert response["status"] == DAEMON_STATUS_OK
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_UNKNOWN

    assert "error" in response[DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_P2P_KEY]["error"]
    assert response[DAEMON_P2P_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_P2P_KEY]["error"]["message"] == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_OK}'."
        )
    caplog.clear()


@mock.patch("monero_health.daemon_rpc_status_check")
@mock.patch("monero_health.daemon_p2p_status_check")
def test_daemon_stati_p2p_unknown(
    mock_daemon_p2p_status, mock_daemon_rpc_status, caplog
):
    rpc_result = {
        "status": DAEMON_STATUS_OK,
        "version": 12,
        "host": "127.0.0.1:18081",
    }
    mock_daemon_rpc_status.return_value = rpc_result

    p2p_result = {
        "status": DAEMON_STATUS_UNKNOWN,
        "host": "127.0.0.1:18080",
        "error": {"error": "Some error.", "message": "Cannot determine status."},
    }
    mock_daemon_p2p_status.return_value = p2p_result

    response = daemon_stati_check(consider_p2p=True)

    assert response["status"] == DAEMON_STATUS_UNKNOWN
    assert response["host"] == "127.0.0.1"

    assert DAEMON_RPC_KEY in response
    assert DAEMON_P2P_KEY in response
    assert "host" in response[DAEMON_RPC_KEY]
    assert response[DAEMON_RPC_KEY]["host"] == "127.0.0.1:18081"
    assert response[DAEMON_RPC_KEY]["status"] == DAEMON_STATUS_OK
    assert response[DAEMON_RPC_KEY]["version"] == 12
    assert "host" in response[DAEMON_P2P_KEY]
    assert response[DAEMON_P2P_KEY]["host"] == "127.0.0.1:18080"
    assert response[DAEMON_P2P_KEY]["status"] == DAEMON_STATUS_UNKNOWN

    assert "error" in response[DAEMON_P2P_KEY]
    assert "error" in response[DAEMON_P2P_KEY]["error"]
    assert "message" in response[DAEMON_P2P_KEY]["error"]
    assert response[DAEMON_P2P_KEY]["error"]["error"] == "Some error.", "Wrong error."
    assert (
        response[DAEMON_P2P_KEY]["error"]["message"] == "Cannot determine status."
    ), "Wrong error."

    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.levelname == "INFO", "Wrong log message."
        json_message = json.loads(record.message)
        assert "message" in json_message, "Wrong log message."
        assert (
            json_message["message"]
            == f"Combined daemon status (RPC, P2P) is '{DAEMON_STATUS_UNKNOWN}'."
        )
    caplog.clear()
