import logging
import datetime
import os
import sys
import json

from monerorpc.authproxy import (
    AuthServiceProxy,
    JSONRPCException,
    HTTP_TIMEOUT as MONERO_RPC_HTTP_TIMEOUT,
)
from requests.exceptions import RequestException

from monero_scripts import connect_to_node

logging.basicConfig()
logger = logging.getLogger("DaemonHealth")
logger.setLevel(logging.DEBUG)
# logging.getLogger("MoneroRPC").setLevel(logging.DEBUG)

URL_DEFAULT = "127.0.0.1"
RPC_PORT_DEFAULT = 18081
P2P_PORT_DEFAULT = 18080
USER_DEFAULT = ""
# Add 'nosec' comment to make bandit ignore [B105:hardcoded_password_string]
PASSWD_DEFAULT = ""  # nosec
OFFSET_DEFAULT = 12
# Possible values: https://docs.python.org/2/library/datetime.html#timedelta-objects
OFFSET_UNIT_DEFAULT = "minutes"
HTTP_TIMEOUT_DEFAULT = MONERO_RPC_HTTP_TIMEOUT

URL = os.environ.get("MONEROD_URL", URL_DEFAULT)
RPC_PORT = os.environ.get("MONEROD_RPC_PORT", RPC_PORT_DEFAULT)
P2P_PORT = os.environ.get("MONEROD_P2P_PORT", P2P_PORT_DEFAULT)
USER = os.environ.get("MONEROD_RPC_USER", USER_DEFAULT)
PASSWD = os.environ.get("MONEROD_RPC_PASSWORD", PASSWD_DEFAULT)
OFFSET = os.environ.get("OFFSET", OFFSET_DEFAULT)
OFFSET_UNIT = os.environ.get("OFFSET_UNIT", OFFSET_UNIT_DEFAULT)
HTTP_TIMEOUT = os.environ.get("HTTP_TIMEOUT", HTTP_TIMEOUT_DEFAULT)

HEALTH_KEY = "health"
LAST_BLOCK_KEY = "last_block"
DAEMON_KEY = "monerod"
DAEMON_P2P_KEY = "p2p"
DAEMON_RPC_KEY = "rpc"

DAEMON_STATUS_OK = "OK"
DAEMON_STATUS_ERROR = "ERROR"
DAEMON_STATUS_UNKNOWN = "UNKNOWN"

DAEMON_STATUS_WEIGHTS = {
    -1: DAEMON_STATUS_UNKNOWN,
    0: DAEMON_STATUS_OK,
    1: DAEMON_STATUS_UNKNOWN,
    2: DAEMON_STATUS_ERROR,
}

DAEMON_STATUS_WEIGHTS_ = {
    DAEMON_STATUS_OK: 0,
    DAEMON_STATUS_UNKNOWN: 1,
    DAEMON_STATUS_ERROR: 2,
}


def is_timestamp_within_offset(
    timestamp=None, now=None, offset: int = OFFSET, offset_unit=OFFSET_UNIT_DEFAULT
) -> bool:
    if not timestamp or not now:
        return None

    block_offset = now - timestamp

    offset = int(offset)

    # Get timedelta (age) for a given block.
    # Use default configuration in case of an error.
    try:
        timedelta_ = {offset_unit: offset}
        delta = datetime.timedelta(**timedelta_)
    except (TypeError) as e:
        logger.warning(
            f"Using default offset of '{OFFSET_DEFAULT} [{OFFSET_UNIT_DEFAULT}]'. Configured wrong offset '{offset} [{offset_unit}]'. Error: '{str(e)}'."
        )
        offset = OFFSET_DEFAULT
        offset_unit = OFFSET_UNIT_DEFAULT
        timedelta_ = {offset_unit: offset}
        delta = datetime.timedelta(**timedelta_)

    return block_offset <= delta, offset, offset_unit


def daemon_last_block_check(
    conn=None,
    url=URL,
    port=RPC_PORT,
    user=USER,
    passwd=PASSWD,
    offset=OFFSET,
    offset_unit=OFFSET_UNIT,
):
    """Check last block status.

    Uses an offset to determine an 'old'/'outdated' last block.
    """

    error = None
    response = None
    block_recent = False
    status = DAEMON_STATUS_UNKNOWN
    last_block_timestamp = -1
    timestamp_obj = None
    block_age = None
    last_block_hash = "---"
    check_timestamp = datetime.datetime.utcnow().replace(microsecond=0)
    try:
        if not conn:
            conn = AuthServiceProxy(
                f"http://{user}@{url}:{port}/json_rpc",
                password=f"{passwd}",
                timeout=HTTP_TIMEOUT,
            )

        logger.info(f"Checking '{url}:{port}'.")

        last_block_header = conn.get_last_block_header()["block_header"]
        last_block_timestamp = float(last_block_header["timestamp"])
        timestamp_obj = datetime.datetime.fromtimestamp(last_block_timestamp)
        last_block_hash = last_block_header["hash"]
        block_recent, offset, offset_unit = is_timestamp_within_offset(
            timestamp=timestamp_obj,
            now=check_timestamp,
            offset=offset,
            offset_unit=offset_unit,
        )
        status = DAEMON_STATUS_OK if block_recent else DAEMON_STATUS_ERROR
        block_age = str(check_timestamp - timestamp_obj)

        response = {}
    except (ValueError, JSONRPCException, RequestException) as e:
        error = {"error": str(e)}

    if response is None:
        if not error:
            error = {"error": f"No response."}

    response = {
        "hash": last_block_hash,
        "block_age": block_age if block_age else -1,
        "block_timestamp": timestamp_obj.isoformat() if timestamp_obj else "---",
        "check_timestamp": check_timestamp.isoformat(),
        "status": status,
        "block_recent": block_recent,
        "block_recent_offset": offset,
        "block_recent_offset_unit": offset_unit,
    }
    response.update({"host": f"{url}:{port}"})

    if status in (DAEMON_STATUS_ERROR, DAEMON_STATUS_UNKNOWN) or error:
        if status == DAEMON_STATUS_ERROR:
            message = (
                f"Last block's timestamp is older than '{offset} [{offset_unit}]'."
            )
        else:
            message = f"Cannot determine status."
        data = {"message": message}

        if not error:
            error = {"error": f"Last block's age is '{block_age}'."}
        data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def daemon_rpc_status_check(
    conn=None, url=URL, port=RPC_PORT, user=USER, passwd=PASSWD
):
    """Check daemon status.

    Uses Monero daemon RPC 'hard_fork_info'.
    """

    error = None
    response = None
    status = DAEMON_STATUS_UNKNOWN
    version = -1
    try:
        if not conn:
            conn = AuthServiceProxy(
                f"http://{user}@{url}:{port}/json_rpc",
                password=f"{passwd}",
                timeout=HTTP_TIMEOUT,
            )

        logger.info(f"Checking '{url}:{port}'.")

        hard_fork_info = conn.hard_fork_info()
        status = hard_fork_info["status"]
        version = hard_fork_info["version"]

        response = {}
    except (ValueError, JSONRPCException, RequestException) as e:
        error = {"error": str(e)}

    if response is None:
        if not error:
            error = {"error": f"No response."}

    response = {"status": status, "version": version}
    response.update({"host": f"{url}:{port}"})

    if status in (DAEMON_STATUS_ERROR, DAEMON_STATUS_UNKNOWN) or error:
        if status == DAEMON_STATUS_ERROR:
            message = f"Status is '{status}'."
        else:
            message = f"Cannot determine status."
        data = {"message": message}

        if not error:
            error = {"error": message}
        data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def daemon_p2p_status_check(url=URL, port=P2P_PORT):
    """Check daemon P2P status.

    Simply connects to the daemon's P2P port to check connectivity.
    Checks Monero daemon P2P status.
    """

    error = None
    response = None
    status = DAEMON_STATUS_UNKNOWN

    try:
        logger.info(f"Checking '{url}:{port}'.")
        connect_to_node.try_to_connect_keep_errors((url, int(port)))
        status = DAEMON_STATUS_OK
    # ConnectionError: connection attempt is aborted /refused or connection aborted by the peer.
    except (ConnectionError) as e:
        error = {"error": str(e)}
        status = DAEMON_STATUS_ERROR
    except Exception as e:
        error = {"error": str(e)}
        status = DAEMON_STATUS_UNKNOWN

    response = {"status": status}
    response.update({"host": f"{url}:{port}"})

    if status in (DAEMON_STATUS_ERROR, DAEMON_STATUS_UNKNOWN) or error:
        if status == DAEMON_STATUS_ERROR:
            message = f"Status is '{status}'."
        else:
            message = f"Cannot determine status."
        data = {"message": message}

        if not error:
            error = {"error": message}
        data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def daemon_stati_check(
    conn=None,
    url=URL,
    port=RPC_PORT,
    p2p_port=P2P_PORT,
    user=USER,
    passwd=PASSWD,
    consider_p2p=False,
):
    """Check combined daemon status.

    Gets Monero daemon status from Monero daemon RPC 'hard_fork_info'.
    Considers Monero daemon P2P status in daemon status, if 'consider_p2p==True'. The result of the P2P check will always be included.
    """

    response = {}
    data = {}

    daemon_rpc_status = DAEMON_STATUS_UNKNOWN
    daemon_p2p_status = DAEMON_STATUS_UNKNOWN

    result = daemon_rpc_status_check(url=url, port=port, user=user, passwd=passwd)
    if result:
        daemon_rpc_status = result.get("status", daemon_rpc_status)
        data.update({DAEMON_RPC_KEY: result})
        response.update(data)

    result = daemon_p2p_status_check(url=url, port=p2p_port)
    if result:
        daemon_p2p_status = result.get("status", daemon_p2p_status)
        data.update({DAEMON_P2P_KEY: result})
        response.update(data)

    stati_to_consider = [daemon_rpc_status]
    if consider_p2p:
        stati_to_consider.append(daemon_p2p_status)

    status = None
    max_weight = -1
    for status_ in stati_to_consider:
        max_weight = max(max_weight, DAEMON_STATUS_WEIGHTS_.get(status_, -1))

    status = DAEMON_STATUS_WEIGHTS[max_weight]

    data = {"status": status, "host": url}
    response.update(data)

    message = f"Combined daemon status (RPC, P2P) is '{status}'."
    data = {"message": message}
    logger.info(json.dumps(data))

    return response


def daemon_combined_status_check(
    conn=None,
    url=URL,
    port=RPC_PORT,
    p2p_port=P2P_PORT,
    user=USER,
    passwd=PASSWD,
    consider_p2p=False,
):
    """Check combined daemon status.

    Checks all stati. Can inlcude dameon's P2P status.

    Gets last block status from offset to determine an 'old'/'outdated' last block.
    Gets Monero daemon status from Monero daemon RPC 'hard_fork_info'.
    Considers Monero daemon P2P status in daemon status, if 'consider_p2p==True'. The result of the P2P check will always be included.
    """

    response = {}

    last_block_status = DAEMON_STATUS_UNKNOWN
    daemon_status = DAEMON_STATUS_UNKNOWN

    result = daemon_last_block_check(url=url, port=port, user=user, passwd=passwd)
    if result:
        last_block_status = result.get("status", last_block_status)
        data = {LAST_BLOCK_KEY: result}
        response.update(data)

    # Check daemon stati.
    result = daemon_stati_check(
        url=url,
        port=port,
        p2p_port=p2p_port,
        user=user,
        passwd=passwd,
        consider_p2p=consider_p2p,
    )
    if result:
        daemon_status = result.get("status", daemon_status)
        data = {DAEMON_KEY: result}
        response.update(data)

    stati_to_consider = (last_block_status, daemon_status)

    status = None
    max_weight = -1
    for status_ in stati_to_consider:
        max_weight = max(max_weight, DAEMON_STATUS_WEIGHTS_.get(status_, -1))

    status = DAEMON_STATUS_WEIGHTS[max_weight]

    data = {"status": status, "host": url}
    response.update(data)

    message = f"Combined status is '{status}'."
    data = {"message": message}
    logger.info(json.dumps(data))

    return response


def main():
    print("----Last block check----:")
    print(
        daemon_last_block_check(
            url=URL,
            port=RPC_PORT,
            user=USER,
            passwd=PASSWD,
            offset=OFFSET,
            offset_unit=OFFSET_UNIT,
        )
    )
    print("----Daemon rpc check----")
    print(daemon_rpc_status_check(url=URL, port=RPC_PORT, user=USER, passwd=PASSWD))
    print("----Daemon p2p check----")
    print(daemon_p2p_status_check(url=URL, port=P2P_PORT))
    print("----Daemon stati check, not considering P2P status----")
    print(daemon_stati_check(url=URL, port=RPC_PORT, p2p_port=P2P_PORT))
    print("----Daemon stati check, also considering P2P status----")
    print(
        daemon_stati_check(url=URL, port=RPC_PORT, p2p_port=P2P_PORT, consider_p2p=True)
    )
    print("----Overall check, not considering P2P status----")
    print(
        daemon_combined_status_check(url=URL, port=RPC_PORT, user=USER, passwd=PASSWD)
    )
    print("----Overall check, also considering P2P status----")
    print(
        daemon_combined_status_check(
            url=URL,
            port=RPC_PORT,
            p2p_port=P2P_PORT,
            user=USER,
            passwd=PASSWD,
            consider_p2p=True,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
