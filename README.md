[![GitHub Release](https://img.shields.io/github/v/release/monero-ecosystem/monero_health.svg)](https://github.com/monero-ecosystem/monero_health/releases)
[![GitHub Tags](https://img.shields.io/github/v/tag/monero-ecosystem/monero_health.svg)](https://github.com/monero-ecosystem/monero_health/tags)

# Monero health

Monero health is supposed to provide information about the Monero daemon health.

There are 3 health checks at the moment:
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
from monero_health.monero_health import daemon_last_block_check
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
from monero_health.mmonero_health import daemon_rpc_status_check
```

No additional configuration needed.

The Monero RPC method used is:
* `hard_fork_info`

### Daemon P2P status
```
from monero_health.mmonero_health import daemon_p2p_status_check
```

No additional configuration is needed.

A socket connection is established, which checks the connectivity to the P2P port.

## Results

### JSON response
This module is not really supposed to be run as a script, rather as a module.

However, it is possible to directly run it as a script. it will then output the complete information. The following only shows part of it, sepcifically the result of the method `daemon_combined_status_check`:
```python
    MONEROD_URL=mainnet.community.xmr.to python -m monero_health.monero_health
    ...
    {
        "last_block": {
            "hash": "2931d04a73c4e286d1e568a0e61ba37fdf175ff6974d343ca136c62ecaaeeee4",
            "block_age": "0:01:57",
            "block_timestamp": "2020-09-23T19:40:02",
            "check_timestamp": "2020-09-23T19:41:59",
            "status": "OK",
            "block_recent": true,
            "block_recent_offset": 12,
            "block_recent_offset_unit": "minutes",
            "host": "mainnet.community.xmr.to:18081"
        },
        "monerod": {
            "rpc": {
                "status": "OK",
                "host": "mainnet.community.xmr.to:18081"
            },
            "p2p": {
                "status": "OK",
                "host": "mainnet.community.xmr.to:18080"
            },
            "status": "OK",
            "host": "mainnet.community.xmr.to",
            "version": 12
        },
        "status": "OK",
        "host": "mainnet.community.xmr.to"
    }
```

When imported as a module the functions can be imported/called separately, like this:
* Last block age:
```python
    from monero_health.mmonero_health import (
        daemon_last_block_check,
    )
    ...
    result = daemon_last_block_check()
    ...
```
* Monero daemaon status:
```python
    from monero_health.mmonero_health import (
        daemon_status_check,
    )
    ...
    result = daemon_status_check()
    ...
```
* Combined daemon status:
```python
    from monero_health.mmonero_health import (
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
    "hash": "---",
    "block_age": -1,
    "block_timestamp": "---",
    "check_timestamp": "2020-09-24T11:52:30",
    "status": "UNKNOWN",
    "block_recent": false,
    "block_recent_offset": 12,
    "block_recent_offset_unit": "minutes",
    "host": "mainnet.community.xmr:18081",
    "error": {
        "message": "Cannot determine status.",
        "error": "-341: Could not establish a connection, original error: 'HTTPConnectionPool(host='mainnet.community.xmr', port=18081): Max retries exceeded with url: /json_rpc (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0f3bb5b150>: Failed to establish a new connection: [Errno -5] No address associated with hostname'))'."
    }
}
```

## Full example

When run as a script (against the XMR.to public node `node.xmr.to`):
```
MONEROD_URL=mainnet.community.xmr.to python -m monero_health.monero_health
```

All health and status checks are run one after another against `mainnet.community.xmr.to`:
* Last block (last block's timestamp).
* Daemon RPC status (port `18081`, RPC method `hard_fork_info`).
* Daemon P2P status (port `18080`).
* Both dameon stati (combined `status` key).
* Run all checks **but do not consider** the daemon P2P status in the resulting `status` key (dameon P2P result is still returned).
* Run all checks **and consider** the daemon P2P status in the resulting `status` key.

The result will look like this:
```
----Last block check----:
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
{"hash": "441380be4c9f10e6ceaec1daeab716cfffab22a8c2adbf765d00fc8d34effe23", "block_age": "0:01:13", "block_timestamp": "2020-09-23T19:50:11", "check_timestamp": "2020-09-23T19:51:24", "status": "OK", "block_recent": true, "block_recent_offset": 12, "block_recent_offset_unit": "minutes", "host": "mainnet.community.xmr.to:18081"}
----Daemon rpc check----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
{"status": "OK", "version": 12, "host": "mainnet.community.xmr.to:18081"}
----Daemon p2p check----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Trying to connect to 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Successfully connected to 'mainnet.community.xmr.to:18080'.
{"status": "OK", "host": "mainnet.community.xmr.to:18080"}
----Daemon stati check, not considering P2P status----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
{"rpc": {"status": "OK", "host": "mainnet.community.xmr.to:18081"}, "status": "OK", "host": "mainnet.community.xmr.to", "version": 12}
----Daemon stati check, also considering P2P status----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Trying to connect to 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Successfully connected to 'mainnet.community.xmr.to:18080'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
{"rpc": {"status": "OK", "host": "mainnet.community.xmr.to:18081"}, "p2p": {"status": "OK", "host": "mainnet.community.xmr.to:18080"}, "status": "OK", "host": "mainnet.community.xmr.to", "version": 12}
----Overall check, not considering P2P status----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
INFO:DaemonHealth:{"message": "Combined status is 'OK'."}
{"last_block": {"hash": "441380be4c9f10e6ceaec1daeab716cfffab22a8c2adbf765d00fc8d34effe23", "block_age": "0:01:20", "block_timestamp": "2020-09-23T19:50:11", "check_timestamp": "2020-09-23T19:51:31", "status": "OK", "block_recent": true, "block_recent_offset": 12, "block_recent_offset_unit": "minutes", "host": "mainnet.community.xmr.to:18081"}, "monerod": {"rpc": {"status": "OK", "host": "mainnet.community.xmr.to:18081"}, "status": "OK", "host": "mainnet.community.xmr.to", "version": 12}, "status": "OK", "host": "mainnet.community.xmr.to"}
----Overall check, also considering P2P status----
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18081'.
INFO:DaemonHealth:Checking 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Trying to connect to 'mainnet.community.xmr.to:18080'.
INFO:monero_scripts.connect_to_node:Successfully connected to 'mainnet.community.xmr.to:18080'.
INFO:DaemonHealth:{"message": "Combined daemon status (RPC, P2P) is 'OK'."}
INFO:DaemonHealth:{"message": "Combined status is 'OK'."}
{"last_block": {"hash": "441380be4c9f10e6ceaec1daeab716cfffab22a8c2adbf765d00fc8d34effe23", "block_age": "0:01:21", "block_timestamp": "2020-09-23T19:50:11", "check_timestamp": "2020-09-23T19:51:32", "status": "OK", "block_recent": true, "block_recent_offset": 12, "block_recent_offset_unit": "minutes", "host": "mainnet.community.xmr.to:18081"}, "monerod": {"rpc": {"status": "OK", "host": "mainnet.community.xmr.to:18081"}, "p2p": {"status": "OK", "host": "mainnet.community.xmr.to:18080"}, "status": "OK", "host": "mainnet.community.xmr.to", "version": 12}, "status": "OK", "host": "mainnet.community.xmr.to"}
```

## Tests and development
```
# Create and activate a virtual environment.
python -m venv venv
. venv/bin/activate

# Install the dependencies.
pip install --upgrade pip-tools
pip-sync requirements.txt

# Run tests.
pytest
```
