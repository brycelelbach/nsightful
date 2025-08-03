"""
Test configuration and fixtures for ncu2markdown.
"""

import io
import tempfile
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
    """Path to the real test CSV file in test_data directory."""
    return Path("test_data/copy_blocked.csv")
