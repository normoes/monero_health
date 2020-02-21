# Monero health

Monero health is supposed to provide information about the Monero daemon health.

There are two health checks at the moment:
* Checking the Monero daemon RPC status using the `hard_fork_info` RPC.
* Checking the Monero daemon P2P status (checks the given P2P port).
* Checking the age of the last block on the daemon using a pre-configured offset.

**_Note_**:

The Monero daemon RPC information are retrieved using the Monero daemon JSON RPC.
The RPC connection is established using [`python-monerorpc`](https://github.com/monero-ecosystem/python-monerorpc).

## Configuration

### Monero daemon RPC connection
The connection to the Monero daemon RPC can be configured using environment variables:

| environment variable | default value |
|----------------------|---------------|
| `MONEROD_URL` | `"127.0.0.1"` |
| `MONEROD_RPC_PORT` | `18081` |
| `MONEROD_P2P_PORT` | `18080` |
| `MONEROD_RPC_USER` | `""` |
| `MONEROD_RPC_PASSWORD` | `""` |

**_Note_**:

The RPC connection is established using [`python-monerorpc`](https://github.com/monero-ecosystem/python-monerorpc).

### Last block age
```
from monero_health import daemon_last_block_check
```

The last block's timestamp is checked against a given pre-configured offset:

| environment variable | default value |
|----------------------|---------------|
| `OFFSET` | `12` |
| `OFFSET_UNIT` | `"minutes"` |

I.e that the last block is considered out-of-date as soon as it becomes older than - in the default case - `12 [minutes]`.

The Monero RPC method used is:
* `get_last_block_header`

### Daemon RPC status
```
from monero_health import daemon_rpc_status_check
```

No additional configuration is needed.

The Monero RPC method used is:
* `hard_fork_info`

### Daemon P2P status
```
from monero_health import daemon_p2p_status_check
```

No additional configuration is needed.

A socket connection is established, which checks the connectivity to the P2P port.

## Results

### JSON response
This module is not really supposed to be run as a script, rather as a module.

However, it is possible to directly run it as a script. it will then output the complete information:
```python
    MONEROD_URL=node.xmr.to python monero_health.py
    # Last block age.
    INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
    {'hash': 'b0f683278980ac65adfa6600c040d38f29f2299912c6c580d04f2f6704bf11d3', 'block_timestamp': '2019-12-19T15:02:16', 'check_timestamp': '2019-12-19T15:08:29', 'status': 'OK', 'block_recent': True, 'block_recent_offset': 12, 'block_recent_offset_unit': 'minutes'}
    # Monero daemon status.
    INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
    {'status': 'OK', 'version': 12}
```

When imported as a module the functions can be imported/called separately, like this:
* Last block age:
```python
    from monero_health import (
        daemon_last_block_check,
    )
    ...
    result = daemon_last_block_check()
    ...
```
* Monero daemaon status:
```python
    from monero_health import (
        daemon_status_check,
    )
    ...
    result = daemon_status_check()
    ...
```
* Combined daemon status:
```python
    from monero_health import (
        daemon_combined_status_check,
    )
    ...
    result = daemon_combined_status_check()
    ...
```

### Possible status values

The `status` returned can have the following values:
* `OK`
  - For a last block that **is not** considered old: (`daemon_last_block_check`)
  - For a daemon with status `OK`: (`daemon_rpc_status_check`, `daemon_p2p_status_check`, `daemon_stati_check`)
  - Every possible status is `OK`: (`daemon_combined_status_check`)
* `ERROR`
  - For a last block that **is** considered old: (`daemon_last_block_check`)
  - For a daemon with status `ERROR`: (`daemon_rpc_status_check`, `daemon_p2p_status_check`, `daemon_stati_check`)
  - At least one possible status is `ERROR`: (`daemon_combined_status_check`)
* `UNKNOWN`
  - In case of a connection error not initiated by the peer (mostly related to HTTP requests): (`daemon_last_block_check`, `daemon_rpc_status_check`, `daemon_p2p_status_check`, `daemon_stati_check`)
  - At least one possible status is `UNKNOWN`: (`daemon_combined_status_check`)

### Errors

In case of an error, an `error` key is added to the responses of:
* `daemon_last_block_check`
* `daemon_rpc_status_check`, `daemon_p2p_status_check`, `daemon_stati_check`
but not to `daemon_combined_status_check`.

This error key always contains the keys:
* `error`
* `message`

Example - No Monero daemon running at `127.0.0.1:18081`:
```
{
    "block_recent": false,
    "block_recent_offset": "12",
    "block_recent_offset_unit": "minutes",
    "block_timestamp": "---",
    "check_timestamp": "2020-01-07T14:53:24",
    "error": {
        "error": "-341: could not establish a connection, original error: HTTPConnectionPool(host='127.0.0.1', port=18081): Max retries exceeded with url: /json_rpc (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fe25e449cd0>: Failed to establish a new connection: [Errno 111] Connection refused'))",
        "message": "Cannot determine daemon status. Daemon: '127.0.0.1:18081'."
    },
    "hash": "---",
    "status": "UNKNOWN"
}
```

## Full example

When run as a script (against the XMR.to public node `node.xmr.to`):
```
MONEROD_URL=node.xmr.to python monero_health.py
```

all health and status checks are run one after another:
* Last block (last block's timestamp).
* Daemon RPC status (port `18081`, RPC method `hard_fork_info`).
* Daemon P2P status (port `18080`).
* Both dameon stati (combined `status` key).
* Run all checks **but do not consider** the daemon P2P status in the resulting `status` key (dameon P2P result is still returned).
* Run all checks **and consider** the daemon P2P status in the resulting `status` key.

The result will look like this:
```
----Last block check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
{'hash': '552cc36a9f0d9417876aaac61ee45b9b4582b054dd4f33e7534f79736318e002', 'block_age': '0:01:54', 'block_timestamp': '2020-02-21T16:34:08', 'check_timestamp': '2020-02-21T16:36:02', 'status': 'OK', 'block_recent': True, 'block_recent_offset': 12, 'block_recent_offset_unit': 'minutes', 'host': 'node.xmr.to:18081'}
----Daemon rpc check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
{'status': 'OK', 'version': 12, 'host': 'node.xmr.to:18081'}
----Daemon p2p check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18080'.
{'status': 'OK', 'host': 'node.xmr.to:18080'}
----Daemon stati check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
INFO:DaemonHealth:Checking 'node.xmr.to:18080'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
{'rpc': {'status': 'OK', 'version': 12, 'host': 'node.xmr.to:18081'}, 'p2p': {'status': 'OK', 'host': 'node.xmr.to:18080'}, 'status': 'OK', 'host': 'node.xmr.to'}
----Overall RPC check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
INFO:DaemonHealth:Checking 'node.xmr.to:18080'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
--OK
INFO:DaemonHealth:{"message": "Combined status is 'OK'."}
{'last_block': {'hash': '552cc36a9f0d9417876aaac61ee45b9b4582b054dd4f33e7534f79736318e002', 'block_age': '0:01:55', 'block_timestamp': '2020-02-21T16:34:08', 'check_timestamp': '2020-02-21T16:36:03', 'status': 'OK', 'block_recent': True, 'block_recent_offset': 12, 'block_recent_offset_unit': 'minutes', 'host': 'node.xmr.to:18081'}, 'monerod': {'rpc': {'status': 'OK', 'version': 12, 'host': 'node.xmr.to:18081'}, 'p2p': {'status': 'OK', 'host': 'node.xmr.to:18080'}, 'status': 'OK', 'host': 'node.xmr.to'}, 'status': 'OK', 'host': 'node.xmr.to'}
----Overall check----:
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
INFO:DaemonHealth:Checking 'node.xmr.to:18080'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
--OK
INFO:DaemonHealth:{"message": "Combined status is 'OK'."}
{'last_block': {'hash': '552cc36a9f0d9417876aaac61ee45b9b4582b054dd4f33e7534f79736318e002', 'block_age': '0:01:56', 'block_timestamp': '2020-02-21T16:34:08', 'check_timestamp': '2020-02-21T16:36:04', 'status': 'OK', 'block_recent': True, 'block_recent_offset': 12, 'block_recent_offset_unit': 'minutes', 'host': 'node.xmr.to:18081'}, 'monerod': {'rpc': {'status': 'OK', 'version': 12, 'host': 'node.xmr.to:18081'}, 'p2p': {'status': 'OK', 'host': 'node.xmr.to:18080'}, 'status': 'OK', 'host': 'node.xmr.to'}, 'status': 'OK', 'host': 'node.xmr.to'}
(venv) [norman ~/git_sources/monero_health.git (master *+%=)]$
```

## Tests
```
# Create and activate a virtual environment.
python -m venv venv
. venv/bin/activate
# Install the dependencies.
pip install --upgrade -r requirements.txt
# Run tests.
pytest
```
