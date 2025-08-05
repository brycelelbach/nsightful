"""
Core functionality for parsing and converting Nsight Systems reports.

This is based on https://github.com/chenyu-jiang/nsys2json and https://github.com/ezyang/nvprof2json.
"""

import sqlite3
import json
from pathlib import Path
import re
from collections import defaultdict
from typing import Optional, List, Dict, Any

NSYS_PID_TO_DEVICE = None

class NsysActivityType:
    KERNEL = "kernel"
    NVTX_CPU = "nvtx"
    NVTX_KERNEL = "nvtx-kernel"
    CUDA_API = "cuda-api"

def convert_nsys_time_to_chrome_trace_time(t):
    """Take a timestamp from nsys (ns) and convert it into us (the default for chrome://tracing)."""
    # For strict correctness, divide by 1000, but this reduces accuracy.
    return t / 1000.

# For reference of the schema, see
# https://docs.nvidia.com/nsight-systems/UserGuide/index.html#exporter-sqlite-schema

def parse_nsys_sqlite_cupti_kernel_events(conn: sqlite3.Connection, strings: dict):
    """
    Copied from the docs:
    CUPTI_ACTIVITY_KIND_KERNEL
    start                       INTEGER   NOT NULL,                    -- Event start timestamp (ns).
    end                         INTEGER   NOT NULL,                    -- Event end timestamp (ns).
    deviceId                    INTEGER   NOT NULL,                    -- Device ID.
    contextId                   INTEGER   NOT NULL,                    -- Context ID.
    streamId                    INTEGER   NOT NULL,                    -- Stream ID.
    correlationId               INTEGER,                               -- REFERENCES CUPTI_ACTIVITY_KIND_RUNTIME(correlationId)
    globalPid                   INTEGER,                               -- Serialized GlobalId.
    demangledName               INTEGER   NOT NULL,                    -- REFERENCES StringIds(id) -- Kernel function name w/ templates
    shortName                   INTEGER   NOT NULL,                    -- REFERENCES StringIds(id) -- Base kernel function name
    mangledName                 INTEGER,                               -- REFERENCES StringIds(id) -- Raw C++ mangled kernel function name
    launchType                  INTEGER,                               -- REFERENCES ENUM_CUDA_KRENEL_LAUNCH_TYPE(id)
    cacheConfig                 INTEGER,                               -- REFERENCES ENUM_CUDA_FUNC_CACHE_CONFIG(id)
    registersPerThread          INTEGER   NOT NULL,                    -- Number of registers required for each thread executing the kernel.
    gridX                       INTEGER   NOT NULL,                    -- X-dimension grid size.
    gridY                       INTEGER   NOT NULL,                    -- Y-dimension grid size.
    gridZ                       INTEGER   NOT NULL,                    -- Z-dimension grid size.
    blockX                      INTEGER   NOT NULL,                    -- X-dimension block size.
    blockY                      INTEGER   NOT NULL,                    -- Y-dimension block size.
    blockZ                      INTEGER   NOT NULL,                    -- Z-dimension block size.
    staticSharedMemory          INTEGER   NOT NULL,                    -- Static shared memory allocated for the kernel (B).
    dynamicSharedMemory         INTEGER   NOT NULL,                    -- Dynamic shared memory reserved for the kernel (B).
    localMemoryPerThread        INTEGER   NOT NULL,                    -- Amount of local memory reserved for each thread (B).
    localMemoryTotal            INTEGER   NOT NULL,                    -- Total amount of local memory reserved for the kernel (B).
    gridId                      INTEGER   NOT NULL,                    -- Unique grid ID of the kernel assigned at runtime.
    sharedMemoryExecuted        INTEGER,                               -- Shared memory size set by the driver.
    graphNodeId                 INTEGER,                               -- REFERENCES CUDA_GRAPH_EVENTS(graphNodeId)
    sharedMemoryLimitConfig     INTEGER                                -- REFERENCES ENUM_CUDA_SHARED_MEM_LIMIT_CONFIG(id)
    """
    per_device_kernel_rows = defaultdict(list)
    per_device_kernel_events = defaultdict(list)
    for row in conn.execute("SELECT * FROM CUPTI_ACTIVITY_KIND_KERNEL"):
        per_device_kernel_rows[row["deviceId"]].append(row)
        event = {
                "name": strings[row["shortName"]],
                "ph": "X", # Complete Event (Begin + End event)
                "cat": "cuda",
                "ts": convert_nsys_time_to_chrome_trace_time(row["start"]),
                "dur": convert_nsys_time_to_chrome_trace_time(row["end"] - row["start"]),
                "tid": "CUDA API {}".format(row["streamId"]),
                "pid": "Device {}".format(row["deviceId"]),
                "args": {
                    # TODO: More
                    },
                }
        per_device_kernel_events[row["deviceId"]].append(event)
    return per_device_kernel_rows, per_device_kernel_events

def link_nsys_pid_with_devices(conn: sqlite3.Connection):
    # map each pid to a device. assumes each pid is associated with a single device
    global NSYS_PID_TO_DEVICE
    if NSYS_PID_TO_DEVICE is None:
        pid_to_device = {}
        for row in conn.execute("SELECT DISTINCT deviceId, globalPid / 0x1000000 % 0x1000000 AS PID FROM CUPTI_ACTIVITY_KIND_KERNEL"):
            assert row["PID"] not in pid_to_device, \
                f"A single PID ({row['PID']}) is associated with multiple devices ({pid_to_device[row['PID']]} and {row['deviceId']})."
            pid_to_device[row["PID"]] = row["deviceId"]
        NSYS_PID_TO_DEVICE = pid_to_device
    return NSYS_PID_TO_DEVICE

def parse_nsys_sqlite_nvtx_events(conn: sqlite3.Connection, strings: dict, event_prefix=None, color_scheme={}):
    """
    Copied from the docs:
    NVTX_EVENTS
    start                       INTEGER   NOT NULL,                    -- Event start timestamp (ns).
    end                         INTEGER,                               -- Event end timestamp (ns).
    eventType                   INTEGER   NOT NULL,                    -- NVTX event type enum value. See docs for specifics.
    rangeId                     INTEGER,                               -- Correlation ID returned from a nvtxRangeStart call.
    category                    INTEGER,                               -- User-controlled ID that can be used to group events.
    color                       INTEGER,                               -- Encoded ARGB color value.
    text                        TEXT,                                  -- Optional text message for non registered strings.
    globalTid                   INTEGER,                               -- Serialized GlobalId.
    endGlobalTid                INTEGER,                               -- Serialized GlobalId. See docs for specifics.
    textId                      INTEGER   REFERENCES StringIds(id),    -- StringId of the NVTX domain registered string.
    domainId                    INTEGER,                               -- User-controlled ID that can be used to group events.
    uint64Value                 INTEGER,                               -- One of possible payload value union members.
    int64Value                  INTEGER,                               -- One of possible payload value union members.
    doubleValue                 REAL,                                  -- One of possible payload value union members.
    uint32Value                 INTEGER,                               -- One of possible payload value union members.
    int32Value                  INTEGER,                               -- One of possible payload value union members.
    floatValue                  REAL,                                  -- One of possible payload value union members.
    jsonTextId                  INTEGER,                               -- One of possible payload value union members.
    jsonText                    TEXT                                   -- One of possible payload value union members.

    NVTX_EVENT_TYPES
    33 - NvtxCategory
    34 - NvtxMark
    39 - NvtxThread
    59 - NvtxPushPopRange
    60 - NvtxStartEndRange
    75 - NvtxDomainCreate
    76 - NvtxDomainDestroy
    """

    if event_prefix is None:
        match_text = ''
    else:
        match_text = " AND "
        if len(event_prefix) == 1:
            match_text += f"NVTX_EVENTS.text LIKE '{event_prefix[0]}%'"
        else:
            match_text += "("
            for idx, prefix in enumerate(event_prefix):
                match_text += f"NVTX_EVENTS.text LIKE '{prefix}%'"
                if idx == len(event_prefix) - 1:
                    match_text += ")"
                else:
                    match_text += " OR "

    per_device_nvtx_rows = defaultdict(list)
    per_device_nvtx_events = defaultdict(list)
    pid_to_device = link_nsys_pid_with_devices(conn)
    # eventType 59 is NvtxPushPopRange, which corresponds to torch.cuda.nvtx.range apis
    for row in conn.execute(f"SELECT start, end, text, textID, globalTid / 0x1000000 % 0x1000000 AS PID, globalTid % 0x1000000 AS TID FROM NVTX_EVENTS WHERE NVTX_EVENTS.eventType == 59{match_text};"):
        name = strings[row["textId"]]
        pid = row['PID']
        tid = row['TID']
        per_device_nvtx_rows[pid_to_device[pid]].append(row)
        assert pid in pid_to_device, f"PID {pid} not found in the pid to device map."
        event = {
                "name": name,
                "ph": "X", # Complete Event (Begin + End event)
                "cat": "nvtx",
                "ts": convert_nsys_time_to_chrome_trace_time(row["start"]),
                "dur": convert_nsys_time_to_chrome_trace_time(row["end"] - row["start"]),
                "tid": "NVTX {}".format(tid),
                "pid": "Host {}".format(pid_to_device[pid]),
                "args": {
                    # TODO: More
                    },
                }
        if color_scheme:
            for key, color in color_scheme.items():
                if re.search(key, name):
                    event["cname"] = color
                    break
        per_device_nvtx_events[pid_to_device[pid]].append(event)
    return per_device_nvtx_rows, per_device_nvtx_events

def parse_nsys_sqlite_cuda_api_events(conn: sqlite3.Connection, strings: dict):
    """
    Copied from the docs:
    CUPTI_ACTIVITY_KIND_RUNTIME
    start                       INTEGER   NOT NULL,                    -- Event start timestamp (ns).
    end                         INTEGER   NOT NULL,                    -- Event end timestamp (ns).
    eventClass                  INTEGER   NOT NULL,                    -- CUDA event class enum value. See docs for specifics.
    globalTid                   INTEGER,                               -- Serialized GlobalId.
    correlationId               INTEGER,                               -- ID used to identify events that this function call has triggered.
    nameId                      INTEGER   NOT NULL   REFERENCES StringIds(id), -- StringId of the function name.
    returnValue                 INTEGER   NOT NULL,                    -- Return value of the function call.
    callchainId                 INTEGER   REFERENCES CUDA_CALLCHAINS(id) -- ID of the attached callchain.
    """
    pid_to_devices = link_nsys_pid_with_devices(conn)
    per_device_api_rows = defaultdict(list)
    per_device_api_events = defaultdict(list)
    # event type 0 is TRACE_PROCESS_EVENT_CUDA_RUNTIME
    for row in conn.execute(f"SELECT start, end, globalTid / 0x1000000 % 0x1000000 AS PID, globalTid % 0x1000000 AS TID, correlationId, nameId FROM CUPTI_ACTIVITY_KIND_RUNTIME;"):
        text = strings[row['nameId']]
        pid = row['PID']
        tid = row['TID']
        correlationId = row['correlationId']
        per_device_api_rows[pid_to_devices[pid]].append(row)
        event = {
                "name": text,
                "ph": "X", # Complete Event (Begin + End event)
                "cat": "cuda_api",
                "ts": convert_nsys_time_to_chrome_trace_time(row["start"]),
                "dur": convert_nsys_time_to_chrome_trace_time(row["end"] - row["start"]),
                "tid": "CUDA API {}".format(tid),
                "pid": "Host {}".format(pid_to_devices[pid]),
                "args": {
                        "correlationId": correlationId,
                    },
                }
        per_device_api_events[pid_to_devices[pid]].append(event)
    return per_device_api_rows, per_device_api_events

def find_overlapping_nvtx_intervals(nvtx_rows, cuda_api_rows):
    mixed_rows = []
    for nvtx_row in nvtx_rows:
        start = nvtx_row["start"]
        end = nvtx_row["end"]
        mixed_rows.append((start, 1, "nvtx", nvtx_row))
        mixed_rows.append((end, -1, "nvtx", nvtx_row))
    for cuda_api_row in cuda_api_rows:
        start = cuda_api_row["start"]
        end = cuda_api_row["end"]
        mixed_rows.append((start, 1, "cuda_api", cuda_api_row))
        mixed_rows.append((end, -1, "cuda_api", cuda_api_row))
    mixed_rows.sort(key=lambda x: (x[0], x[1], x[2]))
    active_intervals = []
    result = defaultdict(list)
    for _, event_type, event_origin, orig_event in mixed_rows:
        if event_type == 1:
            # start
            if event_origin == "nvtx":
                active_intervals.append(orig_event)
            else:
                for event in active_intervals:
                    result[event].append(orig_event)
        else:
            # end
            if event_origin == "nvtx":
                active_intervals.remove(orig_event)
    return result

def link_nvtx_events_to_kernel_events(strings: Dict[str, str],
                                      pid_to_device: Dict[int, int],
                                      per_device_nvtx_rows: Dict[int, list],
                                      per_device_cuda_api_rows: Dict[int, list],
                                      per_device_cuda_kernel_rows: Dict[int, list],
                                      per_device_kernel_events: Dict[int, list]):
    """
    Link NVTX events to cupti kernel events. This is done by first matching
    the nvtx ranges with CUDA API calls by timestamp. Then, retrieve the
    corresponding kernel events using the correlationId from CUDA API calls.
    """
    result = {}
    for device in pid_to_device.values():
        event_map = find_overlapping_nvtx_intervals(per_device_nvtx_rows[device], per_device_cuda_api_rows[device])
        correlation_id_map = defaultdict(dict)
        for cuda_api_row in per_device_cuda_api_rows[device]:
            correlation_id_map[cuda_api_row["correlationId"]]["cuda_api"] = cuda_api_row
        for kernel_row, kernel_trace_event in zip(per_device_cuda_kernel_rows[device], per_device_kernel_events[device]):
            correlation_id_map[kernel_row["correlationId"]]["kernel"] = kernel_row
            correlation_id_map[kernel_row["correlationId"]]["kernel_trace_event"] = kernel_trace_event
        for nvtx_row, cuda_api_rows in event_map.items():
            kernel_start_time = None
            kernel_end_time = None
            for cuda_api_row in cuda_api_rows:
                if "kernel" not in correlation_id_map[cuda_api_row["correlationId"]]:
                    # other cuda api event, ignore
                    continue
                kernel_row = correlation_id_map[cuda_api_row["correlationId"]]["kernel"]
                kernel_trace_event = correlation_id_map[cuda_api_row["correlationId"]]["kernel_trace_event"]
                if "NVTXRegions" not in kernel_trace_event["args"]:
                    kernel_trace_event["args"]["NVTXRegions"] = []
                kernel_trace_event["args"]["NVTXRegions"].append(nvtx_row["text"])
                if kernel_start_time is None or kernel_start_time > kernel_row["start"]:
                    kernel_start_time = kernel_row["start"]
                if kernel_end_time is None or kernel_end_time < kernel_row["end"]:
                    kernel_end_time = kernel_row["end"]
            if kernel_start_time is not None and kernel_end_time is not None:
                result[nvtx_row] = (kernel_start_time, kernel_end_time)
    return result

def parse_nsys_sqlite(conn: sqlite3.Connection, strings: dict, activities=None, event_prefix=None, color_scheme={}):
    if activities is None:
        activities = [NsysActivityType.KERNEL, NsysActivityType.NVTX_CPU, NsysActivityType.NVTX_KERNEL, NsysActivityType.CUDA_API]
    if NsysActivityType.KERNEL in activities or NsysActivityType.NVTX_KERNEL in activities:
        per_device_kernel_rows, per_device_kernel_events = parse_nsys_sqlite_cupti_kernel_events(conn, strings)
    if NsysActivityType.NVTX_CPU in activities or NsysActivityType.NVTX_KERNEL in activities:
        per_device_nvtx_rows, per_device_nvtx_events = parse_nsys_sqlite_nvtx_events(conn, strings, event_prefix=event_prefix, color_scheme=color_scheme)
    if NsysActivityType.CUDA_API in activities or NsysActivityType.NVTX_KERNEL in activities:
        per_device_cuda_api_rows, per_device_cuda_api_events = parse_nsys_sqlite_cuda_api_events(conn, strings)
    if NsysActivityType.NVTX_KERNEL in activities:
        pid_to_device = link_nsys_pid_with_devices(conn)
        nvtx_kernel_event_map = link_nvtx_events_to_kernel_events(strings, pid_to_device, per_device_nvtx_rows, per_device_cuda_api_rows, per_device_kernel_rows, per_device_kernel_events)
    trace_events = []
    if NsysActivityType.KERNEL in activities:
        for k, v in per_device_kernel_events.items():
            trace_events.extend(v)
    if NsysActivityType.NVTX_CPU in activities:
        for k, v in per_device_nvtx_events.items():
            trace_events.extend(v)
    if NsysActivityType.CUDA_API in activities:
        for k, v in per_device_cuda_api_events.items():
            trace_events.extend(v)
    if NsysActivityType.NVTX_KERNEL in activities:
        for nvtx_event, (kernel_start_time, kernel_end_time) in nvtx_kernel_event_map.items():
            event = {
                "name": strings.get(nvtx_event["textId"], nvtx_event["text"] or ""),
                "ph": "X", # Complete Event (Begin + End event)
                "cat": "nvtx-kernel",
                "ts": convert_nsys_time_to_chrome_trace_time(kernel_start_time),
                "dur": convert_nsys_time_to_chrome_trace_time(kernel_end_time - kernel_start_time),
                "tid": "NVTX {}".format(nvtx_event["tid"]),
                "pid": "Device {}".format(pid_to_device[nvtx_event["pid"]]),
                "args": {
                    # TODO: More
                    },
                }
            trace_events.append(event)
    return trace_events


def convert_nsys_sqlite_to_json(
    conn: sqlite3.Connection,
    activities: Optional[List[str]] = None,
    event_prefix: Optional[List[str]] = None,
    color_scheme: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Convert Nsight Systems sqlite database to Chrome Event Trace Format JSON.

    Args:
        conn: SQLite database connection to the Nsight Systems export
        activities: List of activity types to include (kernel, nvtx, nvtx-kernel, cuda-api)
        event_prefix: Filter NVTX events by their names' prefix
        color_scheme: Color scheme mapping for NVTX events

    Returns:
        List of trace events in Chrome Event Trace Format, ready for JSON serialization
    """
    if color_scheme is None:
        color_scheme = {}

    # Extract string mappings from database
    strings = {}
    for r in conn.execute("SELECT id, value FROM StringIds"):
        strings[r["id"]] = r["value"]

    # Parse all events using existing logic
    trace_events = parse_nsys_sqlite(
        conn,
        strings,
        activities=activities,
        event_prefix=event_prefix,
        color_scheme=color_scheme
    )

    # Sort timelines by pid and tid for consistent output
    trace_events.sort(key=lambda x: (x["pid"], x["tid"]))

    return trace_events
