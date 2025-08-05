"""
Tests for Nsightful command line interface functionality.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from nsightful.cli import main


class TestCliMain:
    """Test the main CLI function."""

    def test_help_option(self, capsys):
        """Test that help option displays help message."""
        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "argv", ["nsightful", "--help"]):
                main()

        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "Convert Nsight Compute (NCU) CSV output to Markdown" in captured.out
        assert "ncu" in captured.out
        assert "nsys" in captured.out

    def test_missing_file_argument(self, capsys):
        """Test error when no CSV file argument is provided."""
        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "argv", ["nsightful"]):
                main()

        assert excinfo.value.code == 1  # No subcommand provided
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_nonexistent_file(self, capsys):
        """Test error handling for nonexistent input file."""
        nonexistent_file = "nonexistent_file.csv"

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "argv", ["nsightful", "ncu", nonexistent_file]):
                main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: File '{nonexistent_file}' not found." in captured.err

    def test_directory_as_input(self, capsys, tmp_path):
        """Test error handling when a directory is provided instead of a file."""
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "argv", ["nsightful", "ncu", str(test_dir)]):
                main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: '{test_dir}' is not a file." in captured.err

    def test_successful_conversion_to_stdout(self, capsys, sample_csv_file):
        """Test successful conversion with output to stdout."""
        with patch.object(sys, "argv", ["nsightful", "ncu", str(sample_csv_file)]):
            main()

        captured = capsys.readouterr()
        # Should contain markdown output
        assert "# simple_kernel" in captured.out
        assert "## Speed Of Light" in captured.out
        assert "| Metric Name |" in captured.out

        # Should not have error output
        assert captured.err == ""

    def test_successful_conversion_to_file(self, capsys, sample_csv_file, tmp_path):
        """Test successful conversion with output to file."""
        output_file = tmp_path / "output.md"

        with patch.object(
            sys, "argv", ["nsightful", "ncu", str(sample_csv_file), "-o", str(output_file)]
        ):
            main()

        captured = capsys.readouterr()
        # Should not have stdout output when writing to file
        assert captured.out == ""
        # Should not have error output
        assert captured.err == ""

        # Check that file was created and contains expected content
        assert output_file.exists()
        content = output_file.read_text()
        assert "# simple_kernel" in content
        assert "## Speed Of Light" in content
        assert "| Metric Name |" in content

    def test_long_output_option(self, capsys, sample_csv_file, tmp_path):
        """Test using the long form of the output option."""
        output_file = tmp_path / "output.md"

        with patch.object(
            sys, "argv", ["nsightful", "ncu", str(sample_csv_file), "--output", str(output_file)]
        ):
            main()

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

        # Check that file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "# simple_kernel" in content

    def test_permission_error_input_file(self, capsys, tmp_path):
        """Test error handling for permission denied on input file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        # Mock permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(SystemExit) as excinfo:
                with patch.object(sys, "argv", ["nsightful", "ncu", str(test_file)]):
                    main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert f"Error: Permission denied accessing '{test_file}'." in captured.err

    def test_permission_error_output_file(self, capsys, sample_csv_file, tmp_path):
        """Test error handling for permission denied on output file."""
        output_file = tmp_path / "readonly_output.md"

        # Create a scenario where we can't write to the output file
        def mock_open_func(filename, mode="r", **kwargs):
            if str(output_file) in str(filename) and "w" in mode:
                raise PermissionError("Permission denied")
            return mock_open(read_data="sample csv data").return_value

        with patch("builtins.open", side_effect=mock_open_func):
            with pytest.raises(SystemExit) as excinfo:
                with patch.object(
                    sys, "argv", ["nsightful", "ncu", str(sample_csv_file), "-o", str(output_file)]
                ):
                    main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        # The error message could be either about file processing or permission denied
        assert (
            "Error: During file processing:" in captured.err
            or "Error: Permission denied accessing" in captured.err
        )

    def test_malformed_csv_error(self, capsys, tmp_path):
        """Test error handling for malformed CSV data."""
        malformed_file = tmp_path / "malformed.csv"
        malformed_file.write_text("This is not valid CSV data\nNo headers here")

        with pytest.raises(SystemExit) as excinfo:
            with patch.object(sys, "argv", ["nsightful", "ncu", str(malformed_file)]):
                main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: During file processing:" in captured.err

    def test_utf8_encoding_handling(self, capsys, tmp_path):
        """Test that CLI properly handles UTF-8 encoding."""
        # Create a CSV file with UTF-8 content (including special characters)
        utf8_content = """ID,Process ID,Process Name,Host Name,Kernel Name,Context,Stream,Block Size,Grid Size,Device,CC,Section Name,Metric Name,Metric Unit,Metric Value,Rule Name,Rule Type,Rule Description,Estimated Speedup Type,Estimated Speedup
0,1234,test_app,localhost,test_kernel_🚀,1,0,(256, 1, 1),(128, 1, 1),0,7.5,Speed Of Light,Frequency,Hz,1000000,,,,"""

        utf8_file = tmp_path / "utf8_test.csv"
        utf8_file.write_text(utf8_content, encoding="utf-8")

        with patch.object(sys, "argv", ["nsightful", "ncu", str(utf8_file)]):
            main()

        captured = capsys.readouterr()
        # Should handle UTF-8 content properly
        assert "test_kernel_🚀" in captured.out or "test_kernel" in captured.out
        assert captured.err == ""

    def test_real_test_data_conversion(self, capsys, real_test_csv_file):
        """Test conversion of real test data file."""
        with patch.object(sys, "argv", ["nsightful", "ncu", str(real_test_csv_file)]):
            main()

        captured = capsys.readouterr()
        # Should successfully convert real data
        assert "# copy_blocked" in captured.out
        assert "##" in captured.out  # Should have section headers
        assert "|" in captured.out  # Should have tables
        assert captured.err == ""

        # Should be substantial output
        assert len(captured.out) > 1000

    def test_empty_csv_file(self, capsys, tmp_path):
        """Test handling of empty CSV file."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")

        # This might raise an exception or produce empty output
        # depending on how csv.DictReader handles empty files
        with patch.object(sys, "argv", ["nsightful", "ncu", str(empty_file)]):
            try:
                main()
                captured = capsys.readouterr()
                # If it succeeds, output should be minimal
                assert len(captured.out.strip()) == 0
            except SystemExit as e:
                # If it fails, should be handled gracefully
                assert e.code == 1
                captured = capsys.readouterr()
                assert "Error: During file processing:" in captured.err


class TestCliArgumentParsing:
    """Test argument parsing specifically."""

    def test_csv_file_argument_required(self):
        """Test that CSV file argument is required for ncu subcommand."""
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["nsightful", "ncu"]):
                main()

    def test_output_option_parsing(self, sample_csv_file, tmp_path):
        """Test that output option is parsed correctly."""
        output_file = tmp_path / "test_output.md"

        # Test short form
        with patch.object(
            sys, "argv", ["nsightful", "ncu", str(sample_csv_file), "-o", str(output_file)]
        ):
            main()
        assert output_file.exists()

        # Clean up
        output_file.unlink()

        # Test long form
        with patch.object(
            sys, "argv", ["nsightful", "ncu", str(sample_csv_file), "--output", str(output_file)]
        ):
            main()
        assert output_file.exists()

    def test_help_message_content(self, capsys):
        """Test that help message contains expected information."""
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["nsightful", "ncu", "--help"]):
                main()

        captured = capsys.readouterr()
        help_text = captured.out

        # Should contain usage information
        assert "usage:" in help_text.lower()
        assert "csv_file" in help_text

        # Should contain option descriptions
        assert "-o" in help_text or "--output" in help_text

        # Should contain examples
        assert "nsightful ncu results.csv" in help_text
        assert "nsightful ncu results.csv -o results.md" in help_text

        # Should contain NCU command examples
        assert "ncu --set full" in help_text
        assert "ncu --import" in help_text
