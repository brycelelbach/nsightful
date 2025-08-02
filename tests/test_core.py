"""
Tests for ncu2markdown core functionality.
"""

import io
import pytest
from typing import Dict, Any

from ncu2markdown.core import (
    get_sorted_sections,
    extract_kernel_name,
    format_numeric_value,
    format_rule_type,
    parse_ncu_csv_data,
    add_per_section_markdown,
    convert_ncu_csv_to_flat_markdown
)



class TestGetSortedSections:
    """Test section sorting functionality."""

    def test_sort_known_sections(self):
        """Test that known sections are sorted in the expected order."""
        sections = {
            "Memory Workload": {"data": "mem"},
            "Speed Of Light": {"data": "sol"},
            "Compute Workload": {"data": "comp"},
            "Scheduler": {"data": "sched"}
        }

        sorted_sections = get_sorted_sections(sections)
        section_names = [name for name, _ in sorted_sections]

        # Speed Of Light should come first, followed by Memory Workload, then Compute Workload
        assert section_names.index("Speed Of Light") < section_names.index("Memory Workload")
        assert section_names.index("Memory Workload") < section_names.index("Compute Workload")

    def test_sort_unknown_sections_at_end(self):
        """Test that unknown sections are placed at the end."""
        sections = {
            "Custom Section": {"data": "custom"},
            "Speed Of Light": {"data": "sol"},
            "Another Custom": {"data": "custom2"}
        }

        sorted_sections = get_sorted_sections(sections)
        section_names = [name for name, _ in sorted_sections]

        # Speed Of Light should come first
        assert section_names[0] == "Speed Of Light"
        # Custom sections should be at the end
        assert "Custom Section" in section_names[1:]
        assert "Another Custom" in section_names[1:]

    def test_sort_empty_sections(self):
        """Test sorting with empty sections dictionary."""
        assert get_sorted_sections({}) == []


class TestExtractKernelName:
    """Test kernel name extraction."""

    def test_extract_simple_kernel_name(self):
        """Test extraction from simple kernel names."""
        assert extract_kernel_name("simple_kernel") == "simple_kernel"
        assert extract_kernel_name("my_cuda_function") == "my_cuda_function"

    def test_extract_template_kernel_name(self):
        """Test extraction from template kernel names."""
        full_name = "copy_blocked[v1,cw51cXTLSUwv1sDUaKthrqNgqqmjgOR3W3CwAkMXLaJtQYkOIgxJU0gCqOkEJoHkbttqdVhoqlspQGNFHSgJ5BnXagIA](Array<long long, 1, C, mutable, aligned>, Array<long long, 1, C, mutable, aligned>, long long)"
        assert extract_kernel_name(full_name) == "copy_blocked"

    def test_extract_with_parentheses(self):
        """Test extraction when parentheses come before brackets."""
        assert extract_kernel_name("kernel(int*, float*)") == "kernel"
        assert extract_kernel_name("template_func(T*)") == "template_func"

    def test_extract_with_brackets(self):
        """Test extraction when brackets come before parentheses."""
        assert extract_kernel_name("kernel[T=int](int*)") == "kernel"

    def test_extract_with_spaces(self):
        """Test extraction with spaces in kernel names."""
        assert extract_kernel_name("my kernel[T]") == "my kernel"
        assert extract_kernel_name("  spaced_name  [params]") == "spaced_name"

    def test_extract_no_special_chars(self):
        """Test extraction when no special characters are present."""
        assert extract_kernel_name("simple_name") == "simple_name"


class TestFormatNumericValue:
    """Test numeric value formatting."""

    def test_format_comma_separated_integers(self):
        """Test formatting of comma-separated integers."""
        assert format_numeric_value("1,234,567") == "1,234,567"
        assert format_numeric_value("999") == "999"
        assert format_numeric_value("1,000") == "1,000"

    def test_format_comma_separated_floats(self):
        """Test formatting of comma-separated floats."""
        assert format_numeric_value("1,234.56") == "1,234.56"
        assert format_numeric_value("12,345,678.90") == "12,345,678.90"

    def test_format_large_numbers(self):
        """Test formatting of large numbers without existing commas."""
        # This tests the actual comma addition functionality
        pass  # This function currently only handles existing commas

    def test_format_small_numbers(self):
        """Test formatting of small numbers."""
        assert format_numeric_value("123.45") == "123.45"
        assert format_numeric_value("0.001") == "0.001"

    def test_format_invalid_numbers(self):
        """Test formatting of invalid numeric strings."""
        assert format_numeric_value("not_a_number") == "not_a_number"
        assert format_numeric_value("abc,def") == "abc,def"

    def test_format_empty_string(self):
        """Test formatting of empty strings."""
        assert format_numeric_value("") == ""
        assert format_numeric_value("   ") == "   "


class TestFormatRuleType:
    """Test rule type formatting."""

    def test_format_optimization_rule(self):
        """Test formatting of optimization rules."""
        assert format_rule_type("OPT") == "🔧 **OPTIMIZATION**"

    def test_format_warning_rule(self):
        """Test formatting of warning rules."""
        assert format_rule_type("WRN") == "⚠️ **WARNING**"

    def test_format_info_rule(self):
        """Test formatting of info rules."""
        assert format_rule_type("INF") == "ℹ️ **INFO**"

    def test_format_unknown_rule(self):
        """Test formatting of unknown rule types."""
        assert format_rule_type("UNKNOWN") == "**UNKNOWN**"
        assert format_rule_type("CUSTOM") == "**CUSTOM**"

    def test_format_empty_rule(self):
        """Test formatting of empty rule types."""
        assert format_rule_type("") == "****"


class TestParseNcuCsvData:
    """Test CSV parsing functionality."""

    def test_parse_sample_csv(self, sample_csv_io, expected_parsed_data):
        """Test parsing of sample CSV data."""
        result = parse_ncu_csv_data(sample_csv_io)

        # Check that we have the expected kernels
        assert "simple_kernel" in result
        assert "complex_kernel_template" in result

        # Check Speed Of Light section metrics
        sol_section = result["simple_kernel"]["Speed Of Light"]
        assert len(sol_section["metrics"]) == 3
        assert len(sol_section["rules"]) == 2

        # Check specific metric
        dram_metric = sol_section["metrics"][0]
        assert dram_metric["name"] == "DRAM Frequency"
        assert dram_metric["unit"] == "hz"
        assert dram_metric["value"] == "1,215,000,000"

        # Check specific rule
        sol_rule = sol_section["rules"][0]
        assert sol_rule["name"] == "SOLBottleneck"
        assert sol_rule["type"] == "OPT"
        assert "Memory is more heavily utilized" in sol_rule["description"]

    def test_parse_empty_csv(self, empty_csv_content):
        """Test parsing of empty CSV data."""
        csv_io = io.StringIO(empty_csv_content)
        result = parse_ncu_csv_data(csv_io)
        assert result == {}

    def test_parse_csv_with_empty_sections(self):
        """Test parsing CSV with empty section names."""
        csv_content = '''"ID","Process ID","Process Name","Host Name","Kernel Name","Context","Stream","Block Size","Grid Size","Device","CC","Section Name","Metric Name","Metric Unit","Metric Value","Rule Name","Rule Type","Rule Description","Estimated Speedup Type","Estimated Speedup"
"0","1234","test_app","localhost","test_kernel","1","0","(256, 1, 1)","(128, 1, 1)","0","7.5","","Test Metric","unit","value","","","",""'''

        csv_io = io.StringIO(csv_content)
        result = parse_ncu_csv_data(csv_io)

        # Should skip rows with empty section names
        assert result == {}

    def test_parse_real_test_data(self, real_test_csv_file):
        """Test parsing of real test data file."""
        with open(real_test_csv_file, 'r') as f:
            result = parse_ncu_csv_data(f)

        # Should have copy_blocked kernel
        assert "copy_blocked" in result

        # Should have multiple sections
        kernel_data = result["copy_blocked"]
        assert len(kernel_data) > 0

        # Should have Speed Of Light section (normalized from various forms)
        assert "Speed Of Light" in kernel_data

        # Should have some metrics and rules
        sol_section = kernel_data["Speed Of Light"]
        assert len(sol_section["metrics"]) > 0 or len(sol_section["rules"]) > 0


class TestAddPerSectionMarkdown:
    """Test markdown generation for sections."""

    def test_add_markdown_to_parsed_data(self, sample_csv_io):
        """Test adding markdown to parsed data."""
        parsed_data = parse_ncu_csv_data(sample_csv_io)
        result = add_per_section_markdown(parsed_data)

        # Check that markdown was added
        sol_section = result["simple_kernel"]["Speed Of Light"]
        assert "markdown" in sol_section
        assert "## Speed Of Light" in sol_section["markdown"]

        # Check metrics table
        assert "| Metric Name | Metric Unit | Metric Value |" in sol_section["markdown"]
        assert "| DRAM Frequency | hz | 1,215,000,000 |" in sol_section["markdown"]

        # Check rules
        assert "🔧 **OPTIMIZATION**: Memory is more heavily utilized" in sol_section["markdown"]

    def test_add_markdown_empty_section(self):
        """Test adding markdown to empty section."""
        test_data = {
            "test_kernel": {
                "Empty Section": {
                    "metrics": [],
                    "rules": []
                }
            }
        }

        result = add_per_section_markdown(test_data)
        markdown = result["test_kernel"]["Empty Section"]["markdown"]

        assert "## Empty Section" in markdown
        # Should not contain metrics table or rules
        assert "| Metric Name |" not in markdown
        assert "🔧" not in markdown

    def test_add_markdown_rules_with_speedup(self):
        """Test markdown generation for rules with speedup information."""
        test_data = {
            "test_kernel": {
                "Test Section": {
                    "metrics": [],
                    "rules": [{
                        "name": "TestRule",
                        "type": "WRN",
                        "description": "Test warning message",
                        "speedup_type": "estimated",
                        "speedup": "15.5"
                    }]
                }
            }
        }

        result = add_per_section_markdown(test_data)
        markdown = result["test_kernel"]["Test Section"]["markdown"]

        assert "⚠️ **WARNING**: Test warning message" in markdown
        assert "*Estimated Speedup (estimated): 15.5%*" in markdown


class TestConvertNcuCsvToFlatMarkdown:
    """Test flat markdown conversion."""

    def test_convert_sample_csv_to_markdown(self, sample_csv_io):
        """Test conversion of sample CSV to flat markdown."""
        result = convert_ncu_csv_to_flat_markdown(sample_csv_io)

        # Should have kernel headers
        assert "# simple_kernel" in result
        assert "# complex_kernel_template" in result

        # Should have section headers
        assert "## Speed Of Light" in result
        assert "## Memory Workload" in result
        assert "## Compute Workload" in result

        # Should have metrics tables
        assert "| Metric Name | Metric Unit | Metric Value |" in result

        # Should have rules with formatting
        assert "🔧 **OPTIMIZATION**:" in result
        assert "⚠️ **WARNING**:" in result
        assert "ℹ️ **INFO**:" in result

        # Should have kernel separators
        assert "---" in result

    def test_convert_empty_csv_to_markdown(self, empty_csv_content):
        """Test conversion of empty CSV to markdown."""
        csv_io = io.StringIO(empty_csv_content)
        result = convert_ncu_csv_to_flat_markdown(csv_io)

        # Should be empty or minimal
        assert result.strip() == ""

    def test_convert_real_test_data_to_markdown(self, real_test_csv_file):
        """Test conversion of real test data to markdown."""
        with open(real_test_csv_file, 'r') as f:
            result = convert_ncu_csv_to_flat_markdown(f)

        # Should have copy_blocked kernel
        assert "# copy_blocked" in result

        # Should have proper markdown structure
        assert "##" in result  # Section headers
        assert "|" in result   # Tables

        # Should be substantial content
        assert len(result) > 1000
