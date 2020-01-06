import logging
import datetime
import os
import sys
import json

from monerorpc.authproxy import AuthServiceProxy, JSONRPCException
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ReadTimeout,
    Timeout,
)

logging.basicConfig()
logger = logging.getLogger("DaemonHealth")
logger.setLevel(logging.DEBUG)
# logging.getLogger("MoneroRPC").setLevel(logging.DEBUG)

URL_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 18081
USER_DEFAULT = ""
PASSWD_DEFAULT = ""
OFFSET_DEFAULT = 12
# Possible values: https://docs.python.org/2/library/datetime.html#timedelta-objects
OFFSET_UNIT_DEFAULT = "minutes"

URL = os.environ.get("MONEROD_RPC_URL", URL_DEFAULT)
PORT = os.environ.get("MONEROD_RPC_PORT", PORT_DEFAULT)
USER = os.environ.get("MONEROD_RPC_USER", USER_DEFAULT)
PASSWD = os.environ.get("MONEROD_RPC_PASSWORD", PASSWD_DEFAULT)
OFFSET = os.environ.get("OFFSET", OFFSET_DEFAULT)
OFFSET_UNIT = os.environ.get("OFFSET_UNIT", OFFSET_UNIT_DEFAULT)

DAEMON_STATUS_OK = "OK"
DAEMON_STATUS_ERROR = "ERROR"


def is_timestamp_within_offset(timestamp=None, now=None, offset:int=OFFSET, offset_unit=OFFSET_UNIT_DEFAULT) -> bool:
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
        logger.warning(f"Using default offset of '{OFFSET_DEFAULT} [{OFFSET_UNIT_DEFAULT}]'. Configured wrong offset '{offset} [{offset_unit}]'. Error: '{str(e)}'.")
        offset = OFFSET_DEFAULT
        offset_unit = OFFSET_UNIT_DEFAULT
        timedelta_ = {offset_unit: offset}
        delta = datetime.timedelta(**timedelta_)
        
    return block_offset <= delta, offset, offset_unit


def daemon_last_block_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD, offset=OFFSET, offset_unit=OFFSET_UNIT):
    """Check last block status.

    Uses an offset to determine an 'old'/'outdated' last block.
    """

    error = None
    response = None
    block_recent = False
    status = DAEMON_STATUS_ERROR
    last_block_timestamp = -1
    timestamp_obj = None
    last_block_hash = "---"
    check_timestamp = datetime.datetime.utcnow().replace(microsecond=0)
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}")

        logger.info(f"Checking '{url}:{port}'.")

        last_block_header = conn.get_last_block_header()["block_header"]
        last_block_timestamp = float(last_block_header["timestamp"])
        timestamp_obj = datetime.datetime.fromtimestamp(last_block_timestamp)
        last_block_hash = last_block_header["hash"]
        block_recent, offset, offset_unit = is_timestamp_within_offset(timestamp=timestamp_obj, now=check_timestamp, offset=offset, offset_unit=offset_unit)
        status = DAEMON_STATUS_OK if block_recent else DAEMON_STATUS_ERROR

        response = {}
    except (JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
        error = {"error": str(e)}

    if response is None:
        if not error:
            error = {"error": f"No response from daemon '{url}:{port}'."}

    response = {"hash": last_block_hash, "block_timestamp": timestamp_obj.isoformat() if timestamp_obj else "---", "check_timestamp": check_timestamp.isoformat(), "status": status, "block_recent": block_recent, "block_recent_offset": offset, "block_recent_offset_unit": offset_unit}

    if status == DAEMON_STATUS_ERROR or error:
        data = {"message": f"Last block's timestamp is '{offset} [{offset_unit}]' old. Daemon: '{url}:{port}'."}
        if error:
            data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def daemon_status_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD):
    """Check daemon status.

    Uses Monero daemon RPC 'get_info'.
    """

    error = None
    response = None
    status = DAEMON_STATUS_ERROR
    version = -1
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}")

        logger.info(f"Checking '{url}:{port}'.")

        hard_fork_info = conn.hard_fork_info()
        status = hard_fork_info["status"]
        version = hard_fork_info["version"]

        response = {}
    except (JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
        error = {"error": str(e)}

    if response is None:
        if not error:
            error = {"error": f"No response from daemon '{url}:{port}'."}

    response = {"status": status, "version": version}

    if status == DAEMON_STATUS_ERROR or error:
        data = {"message": f"Dameon status is '{status}'. Daemon: '{url}:{port}'."}
        if error:
            data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def main():
    print(daemon_last_block_check(url=URL, port=PORT, user=USER, passwd=PASSWD, offset=OFFSET, offset_unit=OFFSET_UNIT))
    print(daemon_status_check(url=URL, port=PORT, user=USER, passwd=PASSWD))


if __name__ == "__main__":
    sys.exit(main())
