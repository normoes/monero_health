# Monero health

This is work in progress.

Monero health is supposed to provide information about the Monero daemon health.

There are two health checks at the moment:
* Checking the Monero daemon status using the `get_info` RPC.
* Checking the age of the last block on the daemon using a pre-configured offset.

## Configuration

### Monero daemon connection
The connection to the Monero dameon can be configured using environment variables (also see `docker-compose-template.yml`):

| environment variable | default value |
|----------------------|---------------|
| `MONEROD_RPC_URL` | `"127.0.0.1"` |
| `MONEROD_RPC_PORT` | `18081` |
| `MONEROD_RPC_USER` | `""` |
| `MONEROD_RPC_PASSWORD` | `""` |

The RPC connecton is established using [`python-monerorpc`](https://github.com/monero-ecosystem/python-monerorpc).

### Last block age

The last block's timestamp is checked against a given pre-configured offset:

| environment variable | default value |
|----------------------|---------------|
| `OFFSET` | `12` |
| `OFFSET_UNIT` | `"minutes"` |

I.e that the last block is considered out-of-date as soon as it becomes older than - in the default case - `12 [minutes]`.

## Result

This module is not really supposed to be run as a script, rather than a module.


However, it is possible to directly run it as a script. it will then output the complete information:
```python
    MONEROD_RPC_URL=node.xmr.to python monero_health.py
    # Last block age.
    INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
    {'hash': 'b0f683278980ac65adfa6600c040d38f29f2299912c6c580d04f2f6704bf11d3', 'block_timestamp': '2019-12-19T15:02:16', 'check_timestamp': '2019-12-19T15:08:29.901177', 'block_recent': True, 'block_recent_offset': 12, 'block_recent_offset_unit': 'minutes'}
    # Monero dameon status.
    INFO:DaemonHealth:Checking 'node.xmr.to:18081'.
    {'status': 'OK', 'version': 12}
```

When imported as a module the functions can be imported/called separately, like this:
* Last block age:
```python
    from daemon_health_check import (
        daemon_last_block_check,
    )
    ...
    result = daemon_last_block_check()
    ...
```
* Monero daemaon status:
```python
    from daemon_health_check import (
        daemon_status_check,
    )
    ...
    result = daemon_status_check()
    ...
```
