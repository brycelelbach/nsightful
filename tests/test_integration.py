"""
Integration tests for ncu2markdown.
"""

import subprocess
import sys
from pathlib import Path
import pytest


class TestPackageIntegration:
    """Test package-level integration."""

    def test_package_import(self):
        """Test that the package can be imported successfully."""
        import ncu2markdown

        # Test that main functions are available
        assert hasattr(ncu2markdown, "parse_ncu_csv_data")
        assert hasattr(ncu2markdown, "convert_ncu_csv_to_flat_markdown")
        assert hasattr(ncu2markdown, "display_ncu_data_in_notebook")

        # Test that utility functions are available
        assert hasattr(ncu2markdown, "extract_kernel_name")
        assert hasattr(ncu2markdown, "format_rule_type")

    def test_cli_entry_point(self, real_test_csv_file):
        """Test that the CLI entry point works."""
        # Test help option
        result = subprocess.run(
            [sys.executable, "-m", "ncu2markdown.cli", "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Convert NVIDIA Nsight Compute" in result.stdout

    def test_end_to_end_conversion(self, sample_csv_file):
        """Test end-to-end conversion from CSV to markdown."""
        import ncu2markdown

        # Test the full pipeline
        with open(sample_csv_file, "r") as f:
            # Parse the data
            parsed_data = ncu2markdown.parse_ncu_csv_data(f)
            assert len(parsed_data) > 0

            # Reset file pointer
            f.seek(0)

            # Convert to markdown
            markdown_result = ncu2markdown.convert_ncu_csv_to_flat_markdown(f)
            assert len(markdown_result) > 0
            assert "# simple_kernel" in markdown_result

    def test_version_attribute(self):
        """Test that version attribute is available."""
        import ncu2markdown

        assert hasattr(ncu2markdown, "__version__")
        assert isinstance(ncu2markdown.__version__, str)
        assert len(ncu2markdown.__version__) > 0

    def test_all_exports(self):
        """Test that __all__ exports are working."""
        import ncu2markdown

        for export_name in ncu2markdown.__all__:
            assert hasattr(ncu2markdown, export_name), f"Missing export: {export_name}"


class TestRealDataProcessing:
    """Test processing of real NCU data."""

    def test_real_csv_parsing(self, real_test_csv_file):
        """Test parsing of real CSV data."""
        import ncu2markdown

        with open(real_test_csv_file, "r") as f:
            parsed_data = ncu2markdown.parse_ncu_csv_data(f)

        # Should have parsed the copy_blocked kernel
        assert "copy_blocked" in parsed_data

        # Should have multiple sections
        kernel_data = parsed_data["copy_blocked"]
        assert len(kernel_data) > 3  # Expect multiple sections

        # Should have Speed Of Light section (normalized)
        assert "Speed Of Light" in kernel_data

        # Speed Of Light section should have metrics and/or rules
        sol_section = kernel_data["Speed Of Light"]
        assert len(sol_section["Metrics"]) > 0 or len(sol_section["Rules"]) > 0

    def test_real_csv_markdown_conversion(self, real_test_csv_file):
        """Test markdown conversion of real CSV data."""
        import ncu2markdown

        with open(real_test_csv_file, "r") as f:
            markdown_result = ncu2markdown.convert_ncu_csv_to_flat_markdown(f)

        # Should have substantial content
        assert len(markdown_result) > 5000

        # Should have proper structure
        assert "# copy_blocked" in markdown_result
        assert "## Speed Of Light" in markdown_result

        # Should have tables
        assert "| Metric Name | Metric Unit | Metric Value |" in markdown_result

        # Should have formatted rules
        assert "🔧 **OPTIMIZATION**:" in markdown_result or "⚠️ **WARNING**:" in markdown_result

        # Should have section separators
        assert "---" in markdown_result


class TestErrorHandling:
    """Test error handling across the package."""

    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV data."""
        import ncu2markdown
        import io

        malformed_csv = "This is not CSV data\nJust some random text"
        csv_io = io.StringIO(malformed_csv)

        # Should not crash, might return empty data
        try:
            result = ncu2markdown.parse_ncu_csv_data(csv_io)
            # If it succeeds, should return empty or minimal data
            assert isinstance(result, dict)
        except Exception:
            # If it fails, that's also acceptable for malformed data
            pass

    def test_empty_csv_handling(self):
        """Test handling of empty CSV data."""
        import ncu2markdown
        import io

        # CSV with headers but no data
        empty_csv = """ID,Process ID,Process Name,Host Name,Kernel Name,Context,Stream,Block Size,Grid Size,Device,CC,Section Name,Metric Name,Metric Unit,Metric Value,Rule Name,Rule Type,Rule Description,Estimated Speedup Type,Estimated Speedup"""

        csv_io = io.StringIO(empty_csv)
        result = ncu2markdown.parse_ncu_csv_data(csv_io)

        # Should return empty dict
        assert result == {}

        # Conversion should handle empty data
        csv_io.seek(0)
        markdown_result = ncu2markdown.convert_ncu_csv_to_flat_markdown(csv_io)
        assert markdown_result.strip() == ""
