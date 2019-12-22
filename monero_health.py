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


def daemon_last_block_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD, offset=OFFSET, offset_unit=OFFSET_UNIT, events=None, realm=None):
    error = None
    response = None
    block_recent = False
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}")

        logger.info(f"Checking '{url}:{port}'.")

        last_block_header = conn.get_last_block_header()["block_header"]
        last_block_timestamp = float(last_block_header["timestamp"])
        timestamp_obj = datetime.datetime.fromtimestamp(last_block_timestamp)
        last_block_hash = last_block_header["hash"]
        check_timestamp = datetime.datetime.utcnow()
        block_recent, offset, offset_unit = is_timestamp_within_offset(timestamp=timestamp_obj, now=check_timestamp, offset=offset, offset_unit=offset_unit)

        response = {"hash": last_block_hash, "block_timestamp": timestamp_obj.isoformat(), "check_timestamp": check_timestamp.isoformat(), "block_recent": block_recent, "block_recent_offset": offset, "block_recent_offset_unit": offset_unit}
    except (JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
        error = {"error": str(e)}

    if not response:
        if not error:
            error = {"error": f"No response from daemon '{url}:{port}'."}
        response = {"block_recent": block_recent, "block_recent_offset": offset, "block_recent_offset_unit": offset_unit}
        response.update(error)

    if not block_recent or error:
        data = {"message": f"Last block's timestamp is '{offset} [{offset_unit}]' old. Daemon: '{url}:{port}'."}
        if error:
            data.update(error)
        logger.error(json.dumps(data))
        if events:
            event.trigger(data=json.dumps(data), realm=realm)

    return response


def daemon_status_check(conn=None, url=URL, port=PORT, user=USER, passwd=PASSWD, events=None,realm=None):
    error = None
    response = None
    status = "ERROR"
    try:
        if not conn:
            conn = AuthServiceProxy(f"http://{user}@{url}:{port}/json_rpc", password=f"{passwd}")

        logger.info(f"Checking '{url}:{port}'.")

        hard_fork_info = conn.hard_fork_info()
        status = hard_fork_info["status"]
        version = hard_fork_info["version"]

        response = {"status": status, "version": version}
    except (JSONRPCException, RequestsConnectionError, ReadTimeout, Timeout) as e:
        error = {"error": str(e)}

    if not response:
        if not error:
            error = {"error": f"No response from daemon '{url}:{port}'."}
        response = {"status": status}
        response.update(error)

    if not status == "OK" or error:
        data = {"message": f"Dameon status is '{status}'. Daemon: '{url}:{port}'."}
        if error:
            data.update(error)
        logger.error(json.dumps(data))
        if events:
            event.trigger(data=json.dumps(data), realm=realm)

    return response


def main():
    print(daemon_last_block_check(url=URL, port=PORT, user=USER, passwd=PASSWD, offset=OFFSET, offset_unit=OFFSET_UNIT))
    print(daemon_status_check(url=URL, port=PORT, user=USER, passwd=PASSWD))


if __name__ == "__main__":
    sys.exit(main())
