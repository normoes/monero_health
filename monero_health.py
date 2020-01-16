import logging
import datetime
import os
import sys
import json

from monerorpc.authproxy import AuthServiceProxy, JSONRPCException, HTTP_TIMEOUT as MONERO_RPC_HTTP_TIMEOUT
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
HTTP_TIMEOUT_DEFAULT = MONERO_RPC_HTTP_TIMEOUT

URL = os.environ.get("MONEROD_RPC_URL", URL_DEFAULT)
PORT = os.environ.get("MONEROD_RPC_PORT", PORT_DEFAULT)
USER = os.environ.get("MONEROD_RPC_USER", USER_DEFAULT)
PASSWD = os.environ.get("MONEROD_RPC_PASSWORD", PASSWD_DEFAULT)
OFFSET = os.environ.get("OFFSET", OFFSET_DEFAULT)
OFFSET_UNIT = os.environ.get("OFFSET_UNIT", OFFSET_UNIT_DEFAULT)
HTTP_TIMEOUT = os.environ.get("HTTP_TIMEOUT", HTTP_TIMEOUT_DEFAULT)

HEALTH_KEY = "health"
LAST_BLOCK_KEY = "last_block"
DAEMON_KEY = "monerod"

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
    status = DAEMON_STATUS_UNKNOWN
    last_block_timestamp = -1
    timestamp_obj = None
    block_age = None
    last_block_hash = "---"
    check_timestamp = datetime.datetime.utcnow().replace(microsecond=0)
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}", timeout=HTTP_TIMEOUT)

        logger.info(f"Checking '{url}:{port}'.")

        last_block_header = conn.get_last_block_header()["block_header"]
        last_block_timestamp = float(last_block_header["timestamp"])
        timestamp_obj = datetime.datetime.fromtimestamp(last_block_timestamp)
        last_block_hash = last_block_header["hash"]
        block_recent, offset, offset_unit = is_timestamp_within_offset(timestamp=timestamp_obj, now=check_timestamp, offset=offset, offset_unit=offset_unit)
        status = DAEMON_STATUS_OK if block_recent else DAEMON_STATUS_ERROR
        block_age = str(check_timestamp - timestamp_obj)

        response = {}
    except (ValueError, JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
        error = {"error": str(e)}

    if response is None:
        if not error:
            error = {"error": f"No response."}

    response = {"hash": last_block_hash, "block_age": block_age if block_age else -1, "block_timestamp": timestamp_obj.isoformat() if timestamp_obj else "---", "check_timestamp": check_timestamp.isoformat(), "status": status, "block_recent": block_recent, "block_recent_offset": offset, "block_recent_offset_unit": offset_unit}
    response.update({"host": f"{url}:{port}"})

    if status in (DAEMON_STATUS_ERROR, DAEMON_STATUS_UNKNOWN) or error:
        if status == DAEMON_STATUS_ERROR:
            message = f"Last block's timestamp is older than '{offset} [{offset_unit}]'."
        else:
            message = f"Cannot determine status."
        data = {"message": message}

        if not error:
            error = {"error": f"Last block's age is '{block_age}'."}
        data.update(error)
        response.update({"error": data})
        logger.error(json.dumps(data))

    return response


def daemon_status_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD):
    """Check daemon status.

    Uses Monero daemon RPC 'hard_fork_info'.
    """

    error = None
    response = None
    status = DAEMON_STATUS_UNKNOWN
    version = -1
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}", timeout=HTTP_TIMEOUT)

        logger.info(f"Checking '{url}:{port}'.")

        hard_fork_info = conn.hard_fork_info()
        status = hard_fork_info["status"]
        version = hard_fork_info["version"]

        response = {}
    except (ValueError, JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
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


def daemon_combined_status_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD):
    """Check combined daemon status.

    Gets last block status from offset to determine an 'old'/'outdated' last block. 
    Gets Monero daemon status from Monero daemon RPC 'hard_fork_info'.
    """

    response = {}

    last_block_status = DAEMON_STATUS_UNKNOWN
    last_block_host = ""
    daemon_status = DAEMON_STATUS_UNKNOWN
    daemon_host = ""

    result = daemon_last_block_check(url=url, port=port, user=user, passwd=passwd)
    if result:
        last_block_status = result.get("status", last_block_status)
        last_block_host = result.pop("host", last_block_host)
        data = {LAST_BLOCK_KEY: result}
        response.update(data)

    result = daemon_status_check(url=url, port=port, user=user, passwd=passwd)
    if result:
        daemon_status = result.get("status", daemon_status)
        daemon_host = result.pop("host", daemon_host)
        data = {DAEMON_KEY: result}
        response.update(data)

    stati_to_consider = (last_block_status, daemon_status)

    status = None
    max_weight = -1
    for status_ in stati_to_consider:
        max_weight = max(max_weight, DAEMON_STATUS_WEIGHTS_.get(status_, -1))
   
    status = DAEMON_STATUS_WEIGHTS[max_weight]


    # status = DAEMON_STATUS_ERROR if any([status_ == DAEMON_STATUS_ERROR for status_ in stati_to_consider]) else None
    # if not status:
    #     status = DAEMON_STATUS_UNKNOWN if any([status_ == DAEMON_STATUS_UNKNOWN for status_ in stati_to_consider]) else None
    # if not status:
    #     status = DAEMON_STATUS_OK if all([status_ == DAEMON_STATUS_OK for status_ in stati_to_consider]) else DAEMON_STATUS_UNKOWN

    # 'last_block_host' should always be same as 'daemon_host'.
    data = {"status": status, "host": daemon_host}
    response.update(data)

    message = f"Combined status is '{status}'."
    data = {"message": message}
    logger.info(json.dumps(data))

    return response



def main():
    print(daemon_last_block_check(url=URL, port=PORT, user=USER, passwd=PASSWD, offset=OFFSET, offset_unit=OFFSET_UNIT))
    print(daemon_status_check(url=URL, port=PORT, user=USER, passwd=PASSWD))


if __name__ == "__main__":
    sys.exit(main())
