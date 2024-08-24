#!/usr/bin/env python3

import subprocess
import json

def get_zpool_status():
    """Runs 'zpool list' and 'zpool status' and returns the output."""
    try:
        # Get general information about the pools
        zpool_list_output = subprocess.run(
            ['zpool', 'list', '-Hp', '-o', 'name,free,health'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # Get detailed status for health checks
        zpool_status_output = subprocess.run(
            ['zpool', 'status'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        return zpool_list_output.stdout, zpool_status_output.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing zpool command: {e.stderr}")
        return None, None

def get_arc_stats():
    """Reads ARC stats directly from /proc/spl/kstat/zfs/arcstats."""
    arc_stats = {"hits": "0", "misses": "0"}

    try:
        with open('/proc/spl/kstat/zfs/arcstats') as f:
            for line in f:
                if "hits" in line:
                    arc_stats["hits"] = line.split()[2]
                elif "misses" in line:
                    arc_stats["misses"] = line.split()[2]
        return arc_stats
    except FileNotFoundError:
        print("arcstats not found. Make sure ZFS is properly configured.")
        return arc_stats

def parse_zpool_list(zpool_list_output):
    """Parses the zpool list output to extract useful metrics."""
    pools = []

    for line in zpool_list_output.splitlines():
        if line.strip():
            fields = line.split()
            pool_info = {
                "name": fields[0],
                "free": int(fields[1]),  # Free space is already in bytes due to '-Hp' option
                "health": fields[2],
            }
            pools.append(pool_info)

    return pools

def health_to_status(health):
    """Converts health status to an integer for PRTG compatibility."""
    status_map = {
        "ONLINE": 1,
        "DEGRADED": 2,
        "FAULTED": 3,
        "OFFLINE": 4,
        "REMOVED": 5,
        "UNAVAIL": 6
    }
    return status_map.get(health, 0)  # Return 0 for unknown statuses

def format_for_prtg(pools, arc_stats):
    """Formats the pool status information for PRTG in JSON format."""
    prtg_data = {
        "prtg": {
            "result": [],
            "text": "ZFS Pool Metrics and ARC Stats"
        }
    }

    for pool in pools:
        prtg_data["prtg"]["result"].append({
            "channel": f"Pool {pool['name']} Free",
            "value": pool['free'],
            "unit": "bytes"
        })
        prtg_data["prtg"]["result"].append({
            "channel": f"Pool {pool['name']} Health",
            "value": health_to_status(pool['health']),
            "unit": "zfs.health"
        })

    # Add ARC stats to the output
    prtg_data["prtg"]["result"].append({
        "channel": "ARC Hits",
        "value": int(arc_stats["hits"]),
        "unit": "count"
    })
    prtg_data["prtg"]["result"].append({
        "channel": "ARC Misses",
        "value": int(arc_stats["misses"]),
        "unit": "count"
    })

    return json.dumps(prtg_data, indent=4)

def main():
    zpool_list_output, zpool_status_output = get_zpool_status()
    arc_stats = get_arc_stats()

    if zpool_list_output and zpool_status_output:
        pools = parse_zpool_list(zpool_list_output)
        prtg_output = format_for_prtg(pools, arc_stats)
        print(prtg_output)

if __name__ == "__main__":
    main()
