"""
Test configuration and fixtures for nsightful.
"""

import io
import tempfile
import sqlite3
import json
from pathlib import Path
from typing import Generator, Dict, Any
import pytest


@pytest.fixture
def sample_csv_content() -> str:
    """Provide sample NCU CSV content for testing."""
    return '''"ID","Process ID","Process Name","Host Name","Kernel Name","Context","Stream","Block Size","Grid Size","Device","CC","Section Name","Metric Name","Metric Unit","Metric Value","Rule Name","Rule Type","Rule Description","Estimated Speedup Type","Estimated Speedup"
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","GPU Speed Of Light Throughput","DRAM Frequency","hz","1,215,000,000.00","","","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","GPU Speed Of Light Throughput","SM Frequency","hz","1,410,000,000.50","","","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","GPU Speed Of Light Throughput","Memory Throughput","%","45.7","","","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","SpeedOfLight","","","","SOLBottleneck","OPT","Memory is more heavily utilized than Compute: Look at the Memory Workload Analysis section.","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","SpeedOfLight_RooflineChart","","","","SOLFPRoofline","INF","The kernel achieved 0% of this device's fp32 peak performance.","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","Memory Workload Analysis","Global Load Efficiency","%","90.5","","","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","Memory Workload Analysis","Global Store Efficiency","%","85.2","","","",""
"0","1234","test_app","localhost","simple_kernel(int*)","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","MemoryWorkloadAnalysis","","","","MemoryBound","WRN","Memory bandwidth utilization is high. Consider optimizing memory access patterns.","estimated","15.5"
"0","1234","test_app","localhost","complex_kernel_template[T=int](T*)","1","0","(512, 1, 1)","(64, 1, 1)","0","7.5","Compute Workload Analysis","Executed Ipc Active","inst/cycle","0.85","","","",""
"0","1234","test_app","localhost","complex_kernel_template[T=int](T*)","1","0","(512, 1, 1)","(64, 1, 1)","0","7.5","ComputeWorkloadAnalysis","","","","ComputeBound","OPT","Increase arithmetic intensity to better utilize compute resources.","theoretical","25.0"'''


@pytest.fixture
def sample_csv_file(sample_csv_content: str) -> Generator[Path, None, None]:
    """Create a temporary CSV file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample_csv_content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def sample_csv_io(sample_csv_content: str) -> io.StringIO:
    """Create a StringIO object with sample CSV data."""
    return io.StringIO(sample_csv_content)


@pytest.fixture
def empty_csv_content() -> str:
    """Provide empty CSV content for testing edge cases."""
    return '''"ID","Process ID","Process Name","Host Name","Kernel Name","Context","Stream","Block Size","Grid Size","Device","CC","Section Name","Metric Name","Metric Unit","Metric Value","Rule Name","Rule Type","Rule Description","Estimated Speedup Type","Estimated Speedup"'''


@pytest.fixture
def malformed_csv_content() -> str:
    """Provide malformed CSV content for testing error handling."""
    return """This is not CSV data
Random text
More random text"""


@pytest.fixture
def expected_parsed_data() -> Dict[str, Any]:
    """Expected parsed data structure for sample CSV."""
    return {
        "simple_kernel": {
            "Speed Of Light": {
                "Metrics": {
                    "DRAM Frequency": {
                        "Name": "DRAM Frequency",
                        "Unit": "hz",
                        "Value": "1,215,000,000.00",
                    },
                    "SM Frequency": {
                        "Name": "SM Frequency",
                        "Unit": "hz",
                        "Value": "1,410,000,000.50",
                    },
                    "Memory Throughput": {
                        "Name": "Memory Throughput",
                        "Unit": "%",
                        "Value": "45.7",
                    },
                },
                "Rules": [
                    {
                        "Name": "SOLBottleneck",
                        "Type": "OPT",
                        "Description": "Memory is more heavily utilized than Compute: Look at the Memory Workload Analysis section.",
                        "Speedup_type": "",
                        "Speedup": "",
                    },
                    {
                        "Name": "SOLFPRoofline",
                        "Type": "INF",
                        "Description": "The kernel achieved 0% of this device's fp32 peak performance.",
                        "Speedup_type": "",
                        "Speedup": "",
                    },
                ],
            },
            "Memory Workload": {
                "Metrics": {
                    "Global Load Efficiency": {
                        "Name": "Global Load Efficiency",
                        "Unit": "%",
                        "Value": "90.5",
                    },
                    "Global Store Efficiency": {
                        "Name": "Global Store Efficiency",
                        "Unit": "%",
                        "Value": "85.2",
                    },
                },
                "Rules": [
                    {
                        "Name": "MemoryBound",
                        "Type": "WRN",
                        "Description": "Memory bandwidth utilization is high. Consider optimizing memory access patterns.",
                        "Speedup_type": "estimated",
                        "Speedup": "15.5",
                    }
                ],
            },
        },
        "complex_kernel_template": {
            "Compute Workload": {
                "Metrics": {
                    "Executed Ipc Active": {
                        "Name": "Executed Ipc Active",
                        "Unit": "inst/cycle",
                        "Value": "0.85",
                    }
                },
                "Rules": [
                    {
                        "Name": "ComputeBound",
                        "Type": "OPT",
                        "Description": "Increase arithmetic intensity to better utilize compute resources.",
                        "Speedup_type": "theoretical",
                        "Speedup": "25.0",
                    }
                ],
            }
        },
    }


@pytest.fixture
def real_test_csv_file() -> Path:
    """Path to the real test CSV file in tests directory."""
    return Path("tests/copy_blocked.csv")


@pytest.fixture
def real_sqlite_file() -> Path:
    """Path to the real test SQLite file in tests directory."""
    return Path("tests/power_iteration__baseline.sqlite")


@pytest.fixture
def expected_json_file() -> Path:
    """Path to the expected JSON output file in tests directory."""
    return Path("tests/power_iteration__baseline.json")


@pytest.fixture
def sample_nsys_sqlite_db() -> Generator[Path, None, None]:
    """Create a temporary SQLite database with sample nsys data."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        temp_path = Path(f.name)

    # Create a minimal SQLite database with nsys-like structure
    conn = sqlite3.connect(str(temp_path))
    conn.row_factory = sqlite3.Row

    try:
        # Create StringIds table
        conn.execute("""
            CREATE TABLE StringIds (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Create CUPTI_ACTIVITY_KIND_KERNEL table
        conn.execute("""
            CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL (
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                deviceId INTEGER NOT NULL,
                contextId INTEGER NOT NULL,
                streamId INTEGER NOT NULL,
                correlationId INTEGER,
                globalPid INTEGER,
                demangledName INTEGER NOT NULL,
                shortName INTEGER NOT NULL,
                mangledName INTEGER,
                launchType INTEGER,
                cacheConfig INTEGER,
                registersPerThread INTEGER NOT NULL,
                gridX INTEGER NOT NULL,
                gridY INTEGER NOT NULL,
                gridZ INTEGER NOT NULL,
                blockX INTEGER NOT NULL,
                blockY INTEGER NOT NULL,
                blockZ INTEGER NOT NULL,
                staticSharedMemory INTEGER NOT NULL,
                dynamicSharedMemory INTEGER NOT NULL,
                localMemoryPerThread INTEGER NOT NULL,
                localMemoryTotal INTEGER NOT NULL,
                gridId INTEGER NOT NULL,
                sharedMemoryExecuted INTEGER,
                graphNodeId INTEGER,
                sharedMemoryLimitConfig INTEGER
            )
        """)

        # Create NVTX_EVENTS table
        conn.execute("""
            CREATE TABLE NVTX_EVENTS (
                start INTEGER NOT NULL,
                end INTEGER,
                eventType INTEGER NOT NULL,
                rangeId INTEGER,
                category INTEGER,
                color INTEGER,
                text TEXT,
                globalTid INTEGER,
                endGlobalTid INTEGER,
                textId INTEGER,
                domainId INTEGER,
                uint64Value INTEGER,
                int64Value INTEGER,
                doubleValue REAL,
                uint32Value INTEGER,
                int32Value INTEGER,
                floatValue REAL,
                jsonTextId INTEGER,
                jsonText TEXT
            )
        """)

        # Create CUPTI_ACTIVITY_KIND_RUNTIME table
        conn.execute("""
            CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME (
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                eventClass INTEGER NOT NULL,
                globalTid INTEGER,
                correlationId INTEGER,
                nameId INTEGER NOT NULL,
                returnValue INTEGER NOT NULL,
                callchainId INTEGER
            )
        """)

        # Insert sample string data
        strings = [
            (1, "test_kernel"),
            (2, "nvtx_range"),
            (3, "cudaMalloc"),
        ]
        conn.executemany("INSERT INTO StringIds (id, value) VALUES (?, ?)", strings)

        # Insert sample kernel data
        kernel_data = [
            (1000000, 2000000, 0, 1, 7, 12345, 1234 << 24, 1, 1, None, None, None, 32, 128, 1, 1, 256, 1, 1, 0, 0, 0, 0, 1, None, None, None),
        ]
        conn.executemany("""
            INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL
            (start, end, deviceId, contextId, streamId, correlationId, globalPid, demangledName, shortName, mangledName,
             launchType, cacheConfig, registersPerThread, gridX, gridY, gridZ, blockX, blockY, blockZ,
             staticSharedMemory, dynamicSharedMemory, localMemoryPerThread, localMemoryTotal, gridId,
             sharedMemoryExecuted, graphNodeId, sharedMemoryLimitConfig)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, kernel_data)

        # Insert sample NVTX data
        nvtx_data = [
            (500000, 2500000, 59, None, None, None, None, (1234 << 24) | 9999, None, 2, None, None, None, None, None, None, None, None, None),
        ]
        conn.executemany("""
            INSERT INTO NVTX_EVENTS
            (start, end, eventType, rangeId, category, color, text, globalTid, endGlobalTid, textId, domainId,
             uint64Value, int64Value, doubleValue, uint32Value, int32Value, floatValue, jsonTextId, jsonText)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, nvtx_data)

        # Insert sample CUDA API data
        api_data = [
            (800000, 1200000, 0, (1234 << 24) | 9999, 12345, 3, 0, None),
        ]
        conn.executemany("""
            INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME
            (start, end, eventClass, globalTid, correlationId, nameId, returnValue, callchainId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, api_data)

        conn.commit()

    finally:
        conn.close()

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def sample_nsys_json() -> list:
    """Sample nsys JSON data for testing."""
    return [
        {
            "name": "test_kernel",
            "ph": "X",
            "cat": "cuda",
            "ts": 1000.0,
            "dur": 1000.0,
            "tid": "CUDA API 7",
            "pid": "Device 0",
            "args": {}
        },
        {
            "name": "nvtx_range",
            "ph": "X",
            "cat": "nvtx",
            "ts": 500.0,
            "dur": 2000.0,
            "tid": "NVTX 9999",
            "pid": "Host 0",
            "args": {}
        },
        {
            "name": "cudaMalloc",
            "ph": "X",
            "cat": "cuda_api",
            "ts": 800.0,
            "dur": 400.0,
            "tid": "CUDA API 9999",
            "pid": "Host 0",
            "args": {"correlationId": 12345}
        }
    ]
