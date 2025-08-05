"""
Tests for nsys functionality including parsing and conversion.
"""

import sqlite3
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from nsightful.nsys import (
    convert_nsys_time_to_chrome_trace_time,
    parse_nsys_sqlite_cupti_kernel_events,
    parse_nsys_sqlite_nvtx_events,
    parse_nsys_sqlite_cuda_api_events,
    link_nsys_pid_with_devices,
    find_overlapping_nvtx_intervals,
    link_nvtx_events_to_kernel_events,
    parse_nsys_sqlite,
    convert_nsys_sqlite_to_json,
    NsysActivityType,
)


class TestTimeConversion:
    """Test time conversion utilities."""

    def test_convert_nsys_time_to_chrome_trace_time(self):
        """Test conversion from nanoseconds to microseconds."""
        # Test basic conversion
        assert convert_nsys_time_to_chrome_trace_time(1000) == 1.0
        assert convert_nsys_time_to_chrome_trace_time(1500) == 1.5
        assert convert_nsys_time_to_chrome_trace_time(0) == 0.0

        # Test large numbers
        assert convert_nsys_time_to_chrome_trace_time(1000000000) == 1000000.0

        # Test fractional results
        assert convert_nsys_time_to_chrome_trace_time(1) == 0.001


class TestActivityTypes:
    """Test activity type constants."""

    def test_activity_type_constants(self):
        """Test that activity type constants are defined correctly."""
        assert NsysActivityType.KERNEL == "kernel"
        assert NsysActivityType.NVTX_CPU == "nvtx"
        assert NsysActivityType.NVTX_KERNEL == "nvtx-kernel"
        assert NsysActivityType.CUDA_API == "cuda-api"


class TestPidToDeviceMapping:
    """Test PID to device mapping functionality."""

    def test_link_nsys_pid_with_devices(self):
        """Test linking PIDs to devices."""
        # Create mock database connection
        mock_conn = Mock()
        mock_rows = [
            {"PID": 1234, "deviceId": 0},
            {"PID": 5678, "deviceId": 1},
        ]
        mock_conn.execute.return_value = mock_rows

        result = link_nsys_pid_with_devices(mock_conn)

        expected = {1234: 0, 5678: 1}
        assert result == expected

        # Test that subsequent calls work correctly
        result2 = link_nsys_pid_with_devices(mock_conn)
        assert result2 == expected

    def test_link_nsys_pid_with_devices_duplicate_pid_error(self):
        """Test error handling when a PID is associated with multiple devices."""
        mock_conn = Mock()
        mock_rows = [
            {"PID": 1234, "deviceId": 0},
            {"PID": 1234, "deviceId": 1},  # Same PID, different device
        ]
        mock_conn.execute.return_value = mock_rows

        with pytest.raises(
            AssertionError, match="A single PID.*is associated with multiple devices"
        ):
            link_nsys_pid_with_devices(mock_conn)


class TestKernelEventParsing:
    """Test CUPTI kernel event parsing."""

    def test_parse_nsys_sqlite_cupti_kernel_events(self):
        """Test parsing CUPTI kernel events."""
        mock_conn = Mock()
        strings = {1: "test_kernel", 2: "another_kernel"}

        mock_rows = [
            {
                "deviceId": 0,
                "shortName": 1,
                "start": 1000000,
                "end": 2000000,
                "streamId": 7,
            },
            {
                "deviceId": 1,
                "shortName": 2,
                "start": 3000000,
                "end": 4000000,
                "streamId": 5,
            },
        ]
        mock_conn.execute.return_value = mock_rows

        per_device_rows, per_device_events = parse_nsys_sqlite_cupti_kernel_events(
            mock_conn, strings
        )

        # Check rows are grouped by device
        assert len(per_device_rows[0]) == 1
        assert len(per_device_rows[1]) == 1
        assert per_device_rows[0][0]["shortName"] == 1
        assert per_device_rows[1][0]["shortName"] == 2

        # Check events are properly formatted
        assert len(per_device_events[0]) == 1
        assert len(per_device_events[1]) == 1

        event0 = per_device_events[0][0]
        assert event0["name"] == "test_kernel"
        assert event0["ph"] == "X"
        assert event0["cat"] == "cuda"
        assert event0["ts"] == 1000.0  # 1000000 / 1000
        assert event0["dur"] == 1000.0  # (2000000 - 1000000) / 1000
        assert event0["tid"] == "CUDA API 7"
        assert event0["pid"] == "Device 0"


class TestNvtxEventParsing:
    """Test NVTX event parsing."""

    def test_parse_nsys_sqlite_nvtx_events_basic(self):
        """Test basic NVTX event parsing."""
        mock_conn = Mock()
        strings = {1: "nvtx_range_1", 2: "nvtx_range_2"}

        # Mock the PID to device mapping
        with patch("nsightful.nsys.link_nsys_pid_with_devices") as mock_link:
            mock_link.return_value = {1234: 0, 5678: 1}

            mock_rows = [
                {
                    "start": 1000000,
                    "end": 2000000,
                    "textId": 1,
                    "PID": 1234,
                    "TID": 9999,
                },
                {
                    "start": 3000000,
                    "end": 4000000,
                    "textId": 2,
                    "PID": 5678,
                    "TID": 8888,
                },
            ]
            mock_conn.execute.return_value = mock_rows

            per_device_rows, per_device_events = parse_nsys_sqlite_nvtx_events(mock_conn, strings)

            # Check events are grouped by device
            assert len(per_device_events[0]) == 1
            assert len(per_device_events[1]) == 1

            event0 = per_device_events[0][0]
            assert event0["name"] == "nvtx_range_1"
            assert event0["ph"] == "X"
            assert event0["cat"] == "nvtx"
            assert event0["ts"] == 1000.0
            assert event0["dur"] == 1000.0
            assert event0["tid"] == "NVTX 9999"
            assert event0["pid"] == "Host 0"

    def test_parse_nsys_sqlite_nvtx_events_with_prefix_filter(self):
        """Test NVTX event parsing with prefix filtering."""
        mock_conn = Mock()
        strings = {1: "compute_kernel", 2: "memory_copy"}

        with patch("nsightful.nsys.link_nsys_pid_with_devices") as mock_link:
            mock_link.return_value = {1234: 0}

            # Mock that only events with "compute" prefix are returned
            mock_rows = [
                {
                    "start": 1000000,
                    "end": 2000000,
                    "textId": 1,
                    "PID": 1234,
                    "TID": 9999,
                },
            ]
            mock_conn.execute.return_value = mock_rows

            per_device_rows, per_device_events = parse_nsys_sqlite_nvtx_events(
                mock_conn, strings, event_prefix=["compute"]
            )

            # Verify the SQL query was constructed with the prefix filter
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args[0][0]
            assert "NVTX_EVENTS.text LIKE 'compute%'" in call_args

    def test_parse_nsys_sqlite_nvtx_events_with_color_scheme(self):
        """Test NVTX event parsing with color scheme."""
        mock_conn = Mock()
        strings = {1: "compute_kernel", 2: "memory_copy"}
        color_scheme = {"compute": "thread_state_running", "memory": "thread_state_iowait"}

        with patch("nsightful.nsys.link_nsys_pid_with_devices") as mock_link:
            mock_link.return_value = {1234: 0}

            mock_rows = [
                {
                    "start": 1000000,
                    "end": 2000000,
                    "textId": 1,
                    "PID": 1234,
                    "TID": 9999,
                },
            ]
            mock_conn.execute.return_value = mock_rows

            per_device_rows, per_device_events = parse_nsys_sqlite_nvtx_events(
                mock_conn, strings, color_scheme=color_scheme
            )

            event = per_device_events[0][0]
            assert event["cname"] == "thread_state_running"


class TestCudaApiEventParsing:
    """Test CUDA API event parsing."""

    def test_parse_nsys_sqlite_cuda_api_events(self):
        """Test parsing CUDA API events."""
        mock_conn = Mock()
        strings = {1: "cudaMalloc", 2: "cudaMemcpy"}

        with patch("nsightful.nsys.link_nsys_pid_with_devices") as mock_link:
            mock_link.return_value = {1234: 0, 5678: 1}

            mock_rows = [
                {
                    "start": 1000000,
                    "end": 2000000,
                    "nameId": 1,
                    "PID": 1234,
                    "TID": 9999,
                    "correlationId": 12345,
                },
                {
                    "start": 3000000,
                    "end": 4000000,
                    "nameId": 2,
                    "PID": 5678,
                    "TID": 8888,
                    "correlationId": 67890,
                },
            ]
            mock_conn.execute.return_value = mock_rows

            per_device_rows, per_device_events = parse_nsys_sqlite_cuda_api_events(
                mock_conn, strings
            )

            # Check events are grouped by device
            assert len(per_device_events[0]) == 1
            assert len(per_device_events[1]) == 1

            event0 = per_device_events[0][0]
            assert event0["name"] == "cudaMalloc"
            assert event0["ph"] == "X"
            assert event0["cat"] == "cuda_api"
            assert event0["ts"] == 1000.0
            assert event0["dur"] == 1000.0
            assert event0["tid"] == "CUDA API 9999"
            assert event0["pid"] == "Host 0"
            assert event0["args"]["correlationId"] == 12345


class TestOverlappingIntervals:
    """Test overlapping interval detection."""

    def test_find_overlapping_nvtx_intervals_basic(self):
        """Test finding overlapping intervals."""
        # Create mock sqlite3.Row objects that are hashable
        nvtx_row1 = Mock()
        nvtx_row1.__getitem__ = lambda self, key: {"start": 1000, "end": 3000}[key]
        nvtx_row1.__hash__ = lambda self: hash("nvtx_row1")

        nvtx_row2 = Mock()
        nvtx_row2.__getitem__ = lambda self, key: {"start": 5000, "end": 6000}[key]
        nvtx_row2.__hash__ = lambda self: hash("nvtx_row2")

        cuda_api_row1 = Mock()
        cuda_api_row1.__getitem__ = lambda self, key: {"start": 1500, "end": 2500}[key]
        cuda_api_row1.__hash__ = lambda self: hash("cuda_api_row1")

        cuda_api_row2 = Mock()
        cuda_api_row2.__getitem__ = lambda self, key: {"start": 2000, "end": 5500}[key]
        cuda_api_row2.__hash__ = lambda self: hash("cuda_api_row2")

        nvtx_rows = [nvtx_row1, nvtx_row2]
        cuda_api_rows = [cuda_api_row1, cuda_api_row2]

        result = find_overlapping_nvtx_intervals(nvtx_rows, cuda_api_rows)

        # First NVTX range (1000-3000) should have both CUDA API calls:
        # - cuda_api_row1 (1500-2500) starts while nvtx_row1 is active
        # - cuda_api_row2 (2000-5500) starts while nvtx_row1 is still active
        assert len(result[nvtx_row1]) == 2

        # Second NVTX range (5000-6000) should have no CUDA API calls:
        # - cuda_api_row2 starts at 2000, but nvtx_row2 doesn't start until 5000
        # - By the time nvtx_row2 starts, cuda_api_row2 is already running but not starting
        assert len(result[nvtx_row2]) == 0

    def test_find_overlapping_nvtx_intervals_no_overlap(self):
        """Test case with no overlapping intervals."""
        # Create mock sqlite3.Row objects that are hashable
        nvtx_row = Mock()
        nvtx_row.__getitem__ = lambda self, key: {"start": 1000, "end": 2000}[key]
        nvtx_row.__hash__ = lambda self: hash("nvtx_row")

        cuda_api_row = Mock()
        cuda_api_row.__getitem__ = lambda self, key: {"start": 3000, "end": 4000}[key]
        cuda_api_row.__hash__ = lambda self: hash("cuda_api_row")

        nvtx_rows = [nvtx_row]
        cuda_api_rows = [cuda_api_row]

        result = find_overlapping_nvtx_intervals(nvtx_rows, cuda_api_rows)

        # No overlaps should be found
        assert len(result[nvtx_row]) == 0


class TestEventLinking:
    """Test linking NVTX events to kernel events."""

    def test_link_nvtx_events_to_kernel_events_basic(self):
        """Test basic linking of NVTX events to kernel events."""
        strings = {1: "nvtx_range"}
        pid_to_device = {1234: 0}

        # Create mock sqlite3.Row objects that are hashable
        nvtx_row = Mock()
        nvtx_row.__getitem__ = lambda self, key: {
            "start": 1000,
            "end": 3000,
            "textId": 1,
            "text": None,
            "tid": 9999,
            "pid": 1234,
        }[key]
        nvtx_row.__hash__ = lambda self: hash("nvtx_row")

        cuda_api_row = Mock()
        cuda_api_row.__getitem__ = lambda self, key: {"correlationId": 12345}[key]
        cuda_api_row.__hash__ = lambda self: hash("cuda_api_row")

        kernel_row = Mock()
        kernel_row.__getitem__ = lambda self, key: {
            "correlationId": 12345,
            "start": 1500,
            "end": 2500,
        }[key]
        kernel_row.__hash__ = lambda self: hash("kernel_row")

        per_device_nvtx_rows = {0: [nvtx_row]}
        per_device_cuda_api_rows = {0: [cuda_api_row]}
        per_device_kernel_rows = {0: [kernel_row]}

        kernel_event = {"args": {}}
        per_device_kernel_events = {0: [kernel_event]}

        with patch("nsightful.nsys.find_overlapping_nvtx_intervals") as mock_overlap:
            mock_overlap.return_value = {nvtx_row: [cuda_api_row]}

            result = link_nvtx_events_to_kernel_events(
                strings,
                pid_to_device,
                per_device_nvtx_rows,
                per_device_cuda_api_rows,
                per_device_kernel_rows,
                per_device_kernel_events,
            )

            # Check that NVTX region was added to kernel event
            assert "NVTXRegions" in kernel_event["args"]
            assert kernel_event["args"]["NVTXRegions"] == [
                None
            ]  # textId 1 maps to None in this case

            # Check that timing information was returned
            assert nvtx_row in result
            assert result[nvtx_row] == (1500, 2500)  # kernel start/end times


class TestFullParsing:
    """Test the full parsing pipeline."""

    def test_parse_nsys_sqlite_all_activities(self):
        """Test parsing with all activity types."""
        mock_conn = Mock()
        strings = {1: "test_kernel", 2: "nvtx_range", 3: "cudaMalloc"}

        # Mock all the individual parsing functions
        with patch("nsightful.nsys.parse_nsys_sqlite_cupti_kernel_events") as mock_kernel, patch(
            "nsightful.nsys.parse_nsys_sqlite_nvtx_events"
        ) as mock_nvtx, patch(
            "nsightful.nsys.parse_nsys_sqlite_cuda_api_events"
        ) as mock_api, patch(
            "nsightful.nsys.link_nsys_pid_with_devices"
        ) as mock_link, patch(
            "nsightful.nsys.link_nvtx_events_to_kernel_events"
        ) as mock_link_events:

            # Set up return values
            mock_kernel.return_value = ({0: []}, {0: [{"name": "kernel_event"}]})
            mock_nvtx.return_value = ({0: []}, {0: [{"name": "nvtx_event"}]})
            mock_api.return_value = ({0: []}, {0: [{"name": "api_event"}]})
            mock_link.return_value = {1234: 0}
            mock_link_events.return_value = {}

            result = parse_nsys_sqlite(mock_conn, strings)

            # Should include events from all activity types
            assert len(result) == 3
            event_names = [event["name"] for event in result]
            assert "kernel_event" in event_names
            assert "nvtx_event" in event_names
            assert "api_event" in event_names

    def test_parse_nsys_sqlite_selective_activities(self):
        """Test parsing with selective activity types."""
        mock_conn = Mock()
        strings = {1: "test_kernel"}

        with patch("nsightful.nsys.parse_nsys_sqlite_cupti_kernel_events") as mock_kernel:
            mock_kernel.return_value = ({0: []}, {0: [{"name": "kernel_event"}]})

            result = parse_nsys_sqlite(mock_conn, strings, activities=[NsysActivityType.KERNEL])

            # Should only include kernel events
            assert len(result) == 1
            assert result[0]["name"] == "kernel_event"


class TestConversionToJson:
    """Test the full conversion to JSON."""

    def test_convert_nsys_sqlite_to_json_basic(self):
        """Test basic conversion to JSON format."""
        mock_conn = Mock()

        # Mock string extraction
        mock_strings = [
            {"id": 1, "value": "test_kernel"},
            {"id": 2, "value": "nvtx_range"},
        ]
        mock_conn.execute.return_value = mock_strings

        with patch("nsightful.nsys.parse_nsys_sqlite") as mock_parse:
            mock_events = [
                {"name": "test_kernel", "pid": "Device 0", "tid": "CUDA API 7", "ts": 1000},
                {"name": "nvtx_range", "pid": "Host 0", "tid": "NVTX 9999", "ts": 2000},
            ]
            mock_parse.return_value = mock_events

            result = convert_nsys_sqlite_to_json(mock_conn)

            # Events should be sorted by pid and tid
            assert len(result) == 2
            assert result == mock_events  # Already sorted in this case

    def test_convert_nsys_sqlite_to_json_with_options(self):
        """Test conversion with various options."""
        mock_conn = Mock()
        mock_conn.execute.return_value = [{"id": 1, "value": "test"}]

        with patch("nsightful.nsys.parse_nsys_sqlite") as mock_parse:
            mock_parse.return_value = []

            activities = [NsysActivityType.KERNEL]
            event_prefix = ["compute"]
            color_scheme = {"compute": "red"}

            convert_nsys_sqlite_to_json(
                mock_conn,
                activities=activities,
                event_prefix=event_prefix,
                color_scheme=color_scheme,
            )

            # Verify options were passed through
            mock_parse.assert_called_once()
            call_args = mock_parse.call_args
            assert call_args[1]["activities"] == activities
            assert call_args[1]["event_prefix"] == event_prefix
            assert call_args[1]["color_scheme"] == color_scheme


class TestRealData:
    """Test with real test data."""

    @pytest.fixture
    def real_sqlite_file(self) -> Path:
        """Path to the real test SQLite file."""
        return Path("tests/power_iteration__baseline.sqlite")

    @pytest.fixture
    def expected_json_file(self) -> Path:
        """Path to the expected JSON output."""
        return Path("tests/power_iteration__baseline.json")

    def test_real_sqlite_file_exists(self, real_sqlite_file):
        """Test that the real SQLite test file exists."""
        assert real_sqlite_file.exists()
        assert real_sqlite_file.is_file()

    def test_expected_json_file_exists(self, expected_json_file):
        """Test that the expected JSON file exists."""
        assert expected_json_file.exists()
        assert expected_json_file.is_file()

    def test_real_data_conversion_structure(self, real_sqlite_file):
        """Test that real data conversion produces valid structure."""
        conn = sqlite3.connect(str(real_sqlite_file))
        conn.row_factory = sqlite3.Row

        try:
            result = convert_nsys_sqlite_to_json(conn)

            # Basic structure validation
            assert isinstance(result, list)
            assert len(result) > 0

            # Check first event structure
            first_event = result[0]
            required_fields = ["name", "ph", "cat", "ts", "dur", "tid", "pid"]
            for field in required_fields:
                assert field in first_event

            # Check that we have different categories
            categories = set(event["cat"] for event in result)
            assert len(categories) > 0

        finally:
            conn.close()

    def test_real_data_event_counts(self, real_sqlite_file, expected_json_file):
        """Test that conversion produces expected number of events."""
        # Load expected data
        with open(expected_json_file, "r") as f:
            expected_data = json.load(f)

        # Convert real data
        conn = sqlite3.connect(str(real_sqlite_file))
        conn.row_factory = sqlite3.Row

        try:
            result = convert_nsys_sqlite_to_json(conn)

            # Should produce the same number of events
            assert len(result) == len(expected_data)

        finally:
            conn.close()

    def test_real_data_activity_filtering(self, real_sqlite_file):
        """Test filtering by activity types with real data."""
        conn = sqlite3.connect(str(real_sqlite_file))
        conn.row_factory = sqlite3.Row

        try:
            # Test with only kernel events
            kernel_only = convert_nsys_sqlite_to_json(conn, activities=[NsysActivityType.KERNEL])

            # All events should be kernel events
            for event in kernel_only:
                assert event["cat"] == "cuda"

            # Test with only NVTX events
            nvtx_only = convert_nsys_sqlite_to_json(conn, activities=[NsysActivityType.NVTX_CPU])

            # All events should be NVTX events
            for event in nvtx_only:
                assert event["cat"] == "nvtx"

            # Kernel-only should be different size than NVTX-only
            assert len(kernel_only) != len(nvtx_only)

        finally:
            conn.close()
