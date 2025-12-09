"""
Tests for nsightful Jupyter notebook functionality.
"""

import io
import os
import sqlite3
import json
import re
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from nsightful.notebook import (
    display_ncu_csv_in_notebook,
    display_ncu_simple_markdown,
    display_nsys_sqlite_file_in_notebook,
    display_nsys_sqlite_in_notebook,
    display_nsys_json_in_notebook,
    is_interactive_notebook,
)


class TestIsInteractiveNotebook:
    """Test the is_interactive_notebook function."""

    def test_env_var_false(self, monkeypatch):
        """Test that NSIGHTFUL_USE_WIDGETS=false returns False."""
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")
        assert is_interactive_notebook() is False

    def test_env_var_zero(self, monkeypatch):
        """Test that NSIGHTFUL_USE_WIDGETS=0 returns False."""
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "0")
        assert is_interactive_notebook() is False

    def test_env_var_true(self, monkeypatch):
        """Test that NSIGHTFUL_USE_WIDGETS=true returns True."""
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")
        assert is_interactive_notebook() is True

    def test_env_var_one(self, monkeypatch):
        """Test that NSIGHTFUL_USE_WIDGETS=1 returns True."""
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "1")
        assert is_interactive_notebook() is True


class TestDisplayNcuDataInNotebook:
    """Test the display_ncu_csv_in_notebook function."""

    def test_missing_dependencies_handling(self, capsys, sample_csv_io):
        """Test handling when IPython is not available."""
        with patch("builtins.__import__", side_effect=ImportError):
            display_ncu_csv_in_notebook(sample_csv_io)

        captured = capsys.readouterr()
        assert "Error: IPython is required for this function" in captured.out
        assert "pip install ipython" in captured.out

    def test_successful_display_basic(self, monkeypatch, sample_csv_io):
        """Test that display function handles sample data without crashing."""
        # Enable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")

        # Mock the imports at the function level
        mock_widgets = Mock()
        mock_display = Mock()
        mock_html = Mock()
        mock_markdown = Mock()
        mock_clear_output = Mock()

        # Create mock widgets
        mock_dropdown = Mock()
        mock_output = Mock()
        mock_tab = Mock()

        # Make output behave like a context manager
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)

        mock_widgets.Dropdown.return_value = mock_dropdown
        mock_widgets.Output.return_value = mock_output
        mock_widgets.Tab.return_value = mock_tab
        mock_widgets.Layout.return_value = Mock()

        # Mock the imports
        with patch.dict(
            "sys.modules",
            {
                "ipywidgets": mock_widgets,
                "IPython.display": MagicMock(
                    display=mock_display,
                    HTML=mock_html,
                    Markdown=mock_markdown,
                    clear_output=mock_clear_output,
                ),
            },
        ):
            # This should not raise any exceptions
            display_ncu_csv_in_notebook(sample_csv_io)

            # Verify that widgets were created
            mock_widgets.Dropdown.assert_called_once()
            mock_widgets.Output.assert_called()

    def test_real_data_parsing(self, monkeypatch, real_test_csv_file):
        """Test that real data can be parsed without errors."""
        if not real_test_csv_file.exists():
            pytest.skip(f"Real test file {real_test_csv_file} not found")

        # Enable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")

        # Mock the imports using sys.modules since they're imported inside the function
        mock_widgets = Mock()
        mock_display = Mock()
        mock_html = Mock()
        mock_markdown = Mock()
        mock_clear_output = Mock()

        # Set up widget mocks
        mock_output = Mock()
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)
        mock_widgets.Dropdown.return_value = Mock()
        mock_widgets.Output.return_value = mock_output
        mock_widgets.Tab.return_value = Mock()
        mock_widgets.Layout.return_value = Mock()

        with patch.dict(
            "sys.modules",
            {
                "ipywidgets": mock_widgets,
                "IPython.display": MagicMock(
                    display=mock_display,
                    HTML=mock_html,
                    Markdown=mock_markdown,
                    clear_output=mock_clear_output,
                ),
            },
        ):
            with open(real_test_csv_file, "r") as f:
                # This should not raise any exceptions
                display_ncu_csv_in_notebook(f)

    def test_empty_data_handling(self, monkeypatch):
        """Test handling of empty CSV data."""
        # Enable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")

        empty_csv = io.StringIO("")

        # Mock the imports using sys.modules since they're imported inside the function
        mock_widgets = Mock()
        mock_display = Mock()
        mock_html = Mock()
        mock_markdown = Mock()
        mock_clear_output = Mock()

        # Set up widget mocks
        mock_output = Mock()
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)
        mock_widgets.Dropdown.return_value = Mock()
        mock_widgets.Output.return_value = mock_output
        mock_widgets.Tab.return_value = Mock()
        mock_widgets.Layout.return_value = Mock()

        with patch.dict(
            "sys.modules",
            {
                "ipywidgets": mock_widgets,
                "IPython.display": MagicMock(
                    display=mock_display,
                    HTML=mock_html,
                    Markdown=mock_markdown,
                    clear_output=mock_clear_output,
                ),
            },
        ):
            # This should handle empty data gracefully
            display_ncu_csv_in_notebook(empty_csv)

    def test_widget_creation_flow(self, monkeypatch, sample_csv_io):
        """Test the widget creation and interaction flow."""
        # Enable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")

        mock_widgets = Mock()
        mock_display = Mock()
        mock_html = Mock()
        mock_markdown = Mock()
        mock_clear_output = Mock()

        # Set up dropdown mock
        mock_dropdown = Mock()
        mock_dropdown.value = "simple_kernel"
        mock_widgets.Dropdown.return_value = mock_dropdown

        # Set up output mock
        mock_output = Mock()
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)
        mock_widgets.Output.return_value = mock_output

        # Set up tab mock
        mock_tab = Mock()
        mock_widgets.Tab.return_value = mock_tab

        mock_widgets.Layout.return_value = Mock()

        with patch.dict(
            "sys.modules",
            {
                "ipywidgets": mock_widgets,
                "IPython.display": MagicMock(
                    display=mock_display,
                    HTML=mock_html,
                    Markdown=mock_markdown,
                    clear_output=mock_clear_output,
                ),
            },
        ):
            display_ncu_csv_in_notebook(sample_csv_io)

            # Verify dropdown was created with correct options
            mock_widgets.Dropdown.assert_called_once()
            call_args = mock_widgets.Dropdown.call_args[1]
            assert "simple_kernel" in call_args["options"]
            assert "complex_kernel_template" in call_args["options"]

            # Verify tab creation
            mock_widgets.Tab.assert_called_once()

            # Verify display calls
            assert mock_display.call_count >= 2  # At least dropdown and output area

    def test_colab_import_handling(self, monkeypatch, sample_csv_io):
        """Test that Google Colab imports are handled gracefully."""
        # Enable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "true")

        # Mock successful widget imports
        mock_widgets = Mock()
        mock_display = Mock()
        mock_widgets.Dropdown.return_value = Mock()
        mock_widgets.Output.return_value = Mock()
        mock_widgets.Tab.return_value = Mock()
        mock_widgets.Layout.return_value = Mock()

        # Mock output context manager
        mock_output = mock_widgets.Output.return_value
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)

        with patch.dict(
            "sys.modules",
            {
                "ipywidgets": mock_widgets,
                "IPython.display": MagicMock(
                    display=mock_display, HTML=Mock(), Markdown=Mock(), clear_output=Mock()
                ),
                # Mock google.colab to not exist
                "google": None,
                "google.colab": None,
            },
        ):
            # This should not raise any exceptions even if google.colab is not available
            display_ncu_csv_in_notebook(sample_csv_io)

            # Should still create widgets even if Colab import fails
            mock_widgets.Dropdown.assert_called_once()


class TestSimpleMarkdownDisplay:
    """Test the simple markdown fallback display (when widgets are disabled)."""

    def test_simple_markdown_fallback_when_widgets_disabled(self, monkeypatch, sample_csv_io):
        """Test that simple markdown is used when NSIGHTFUL_USE_WIDGETS=false."""
        # Disable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")

        mock_display = Mock()
        mock_markdown = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            display_ncu_csv_in_notebook(sample_csv_io)

            # Should call display with Markdown (not widgets)
            assert mock_display.call_count >= 1
            assert mock_markdown.call_count >= 1

    def test_simple_markdown_displays_kernel_names(self, monkeypatch, sample_csv_io):
        """Test that simple markdown displays kernel names as headers."""
        # Disable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")

        mock_display = Mock()
        markdown_calls = []

        def capture_markdown(text):
            markdown_calls.append(text)
            return Mock()

        mock_markdown = Mock(side_effect=capture_markdown)

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            display_ncu_csv_in_notebook(sample_csv_io)

            # Check that kernel names appear in the markdown calls
            all_markdown = " ".join(markdown_calls)
            assert "simple_kernel" in all_markdown
            assert "complex_kernel_template" in all_markdown

    def test_simple_markdown_displays_summary(self, monkeypatch, sample_csv_io):
        """Test that simple markdown displays a summary section."""
        # Disable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")

        mock_display = Mock()
        markdown_calls = []

        def capture_markdown(text):
            markdown_calls.append(text)
            return Mock()

        mock_markdown = Mock(side_effect=capture_markdown)

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            display_ncu_csv_in_notebook(sample_csv_io)

            # Check that Summary appears in the markdown
            all_markdown = " ".join(markdown_calls)
            assert "Summary" in all_markdown

    def test_display_ncu_simple_markdown_directly(self, sample_csv_io):
        """Test calling display_ncu_simple_markdown directly."""
        from nsightful.ncu import parse_ncu_csv, add_per_section_ncu_markdown

        mock_display = Mock()
        mock_markdown = Mock()

        ncu_dict = add_per_section_ncu_markdown(parse_ncu_csv(sample_csv_io))

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            display_ncu_simple_markdown(ncu_dict)

            # Should call display multiple times (kernel titles, summary, sections)
            assert mock_display.call_count >= 1
            assert mock_markdown.call_count >= 1

    def test_simple_markdown_with_empty_data(self, monkeypatch):
        """Test simple markdown display with empty CSV data."""
        # Disable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")

        empty_csv = io.StringIO("")

        mock_display = Mock()
        mock_markdown = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            # Should handle empty data gracefully
            display_ncu_csv_in_notebook(empty_csv)

    def test_simple_markdown_with_real_data(self, monkeypatch, real_test_csv_file):
        """Test simple markdown display with real test data."""
        if not real_test_csv_file.exists():
            pytest.skip(f"Real test file {real_test_csv_file} not found")

        # Disable widgets via environment variable
        monkeypatch.setenv("NSIGHTFUL_USE_WIDGETS", "false")

        mock_display = Mock()
        mock_markdown = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(
                    display=mock_display,
                    Markdown=mock_markdown,
                ),
            },
        ):
            with open(real_test_csv_file, "r") as f:
                # This should not raise any exceptions
                display_ncu_csv_in_notebook(f)

            # Should have displayed markdown content
            assert mock_display.call_count >= 1
            assert mock_markdown.call_count >= 1


class TestDisplayNsysDataInNotebook:
    """Test the nsys notebook display functions."""

    @pytest.fixture
    def real_sqlite_file(self) -> Path:
        """Path to the real test SQLite file."""
        return Path("tests/power_iteration__baseline.sqlite")

    @pytest.fixture
    def expected_json_file(self) -> Path:
        """Path to the expected JSON output."""
        return Path("tests/power_iteration__baseline.json")

    @pytest.fixture
    def sample_nsys_json(self):
        """Sample nsys JSON data for testing."""
        return [
            {
                "name": "test_kernel",
                "ph": "X",
                "cat": "cuda",
                "ts": 1000.0,
                "dur": 500.0,
                "tid": "CUDA API 7",
                "pid": "Device 0",
                "args": {},
            },
            {
                "name": "nvtx_range",
                "ph": "X",
                "cat": "nvtx",
                "ts": 2000.0,
                "dur": 300.0,
                "tid": "NVTX 9999",
                "pid": "Host 0",
                "args": {},
            },
        ]

    def test_display_nsys_json_missing_dependencies(self, capsys, sample_nsys_json):
        """Test handling when IPython is not available."""
        with patch("builtins.__import__", side_effect=ImportError):
            display_nsys_json_in_notebook(sample_nsys_json)

        captured = capsys.readouterr()
        assert "Error: ipywidgets and IPython are required" in captured.out
        assert "pip install ipywidgets" in captured.out

    def test_display_nsys_json_basic(self, sample_nsys_json):
        """Test basic nsys JSON display functionality."""
        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            display_nsys_json_in_notebook(sample_nsys_json)

            # Should call display with HTML
            mock_display.assert_called_once()
            mock_html.assert_called_once()

            # Check that HTML contains expected elements
            html_call = mock_html.call_args[0][0]
            assert re.search(r"open-perfetto-[a-f0-9]{8}", html_call)
            assert "https://ui.perfetto.dev" in html_call
            assert "postMessage" in html_call

    def test_display_nsys_json_with_custom_title_and_filename(self, sample_nsys_json):
        """Test nsys JSON display with custom title and filename."""
        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            display_nsys_json_in_notebook(
                sample_nsys_json, title="Custom Title", filename="custom.json"
            )

            # Check that custom title and filename are in the HTML
            html_call = mock_html.call_args[0][0]
            assert "Custom Title" in html_call
            assert "custom.json" in html_call

    def test_display_nsys_sqlite_file_in_notebook(self, real_sqlite_file):
        """Test displaying nsys SQLite file in notebook."""
        if not real_sqlite_file.exists():
            pytest.skip(f"Real test file {real_sqlite_file} not found")

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            # This should not raise any exceptions
            display_nsys_sqlite_file_in_notebook(str(real_sqlite_file))

            # Should call display with HTML
            mock_display.assert_called_once()
            mock_html.assert_called_once()

    def test_display_nsys_sqlite_in_notebook(self, real_sqlite_file):
        """Test displaying nsys SQLite connection in notebook."""
        if not real_sqlite_file.exists():
            pytest.skip(f"Real test file {real_sqlite_file} not found")

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            conn = sqlite3.connect(str(real_sqlite_file))
            conn.row_factory = sqlite3.Row

            try:
                # This should not raise any exceptions
                display_nsys_sqlite_in_notebook(conn)

                # Should call display with HTML
                mock_display.assert_called_once()
                mock_html.assert_called_once()
            finally:
                conn.close()

    def test_display_nsys_sqlite_file_with_custom_params(self, real_sqlite_file):
        """Test displaying nsys SQLite file with custom parameters."""
        if not real_sqlite_file.exists():
            pytest.skip(f"Real test file {real_sqlite_file} not found")

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            display_nsys_sqlite_file_in_notebook(str(real_sqlite_file), title="Custom Nsys Title")

            # Check that custom title is used
            html_call = mock_html.call_args[0][0]
            assert "Custom Nsys Title" in html_call
            # The filename should be the sqlite file path
            assert str(real_sqlite_file) in html_call

    def test_nsys_json_base64_encoding(self, sample_nsys_json):
        """Test that JSON data is properly base64 encoded."""
        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            display_nsys_json_in_notebook(sample_nsys_json)

            # Get the HTML content
            html_call = mock_html.call_args[0][0]

            # Should contain base64 encoded data
            assert re.search(r"const B64_[a-f0-9]{8}", html_call)
            assert re.search(r"b64ToArrayBuffer_[a-f0-9]{8}", html_call)

            # The base64 string should be valid (we can't easily decode it here without
            # importing base64, but we can check it's present and looks reasonable)
            b64_match = re.search(
                r'const B64_[a-f0-9]{8}\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', html_call
            )
            assert b64_match is not None
            b64_string = b64_match.group(1)
            assert len(b64_string) > 0

    def test_perfetto_integration_javascript(self, sample_nsys_json):
        """Test that the JavaScript for Perfetto integration is correct."""
        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            display_nsys_json_in_notebook(sample_nsys_json)

            html_call = mock_html.call_args[0][0]

            # Check for key JavaScript elements
            assert re.search(r"addEventListener\('click', openPerfetto_[a-f0-9]{8}\)", html_call)
            assert "window.open('https://ui.perfetto.dev/#!/')" in html_call
            assert "postMessage('PING', '*')" in html_call
            assert "e.data === 'PONG'" in html_call
            assert "perfetto: {" in html_call
            assert re.search(r"buffer: b64ToArrayBuffer_[a-f0-9]{8}\(B64_[a-f0-9]{8}\)", html_call)

    def test_nsys_empty_json_handling(self):
        """Test handling of empty JSON data."""
        empty_json = []

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            # Should handle empty data gracefully
            display_nsys_json_in_notebook(empty_json)

            # Should still create the display
            mock_display.assert_called_once()
            mock_html.assert_called_once()

    def test_nsys_large_json_handling(self):
        """Test handling of large JSON data."""
        # Create a large dataset
        large_json = []
        for i in range(1000):
            large_json.append(
                {
                    "name": f"kernel_{i}",
                    "ph": "X",
                    "cat": "cuda",
                    "ts": i * 1000.0,
                    "dur": 100.0,
                    "tid": f"CUDA API {i % 10}",
                    "pid": f"Device {i % 2}",
                    "args": {"iteration": i},
                }
            )

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            # Should handle large data without issues
            display_nsys_json_in_notebook(large_json)

            mock_display.assert_called_once()
            mock_html.assert_called_once()

            # Check that the data was encoded
            html_call = mock_html.call_args[0][0]
            assert re.search(r"const B64_[a-f0-9]{8}", html_call)

    def test_nsys_json_special_characters(self):
        """Test handling of JSON data with special characters."""
        special_json = [
            {
                "name": "kernel_with_特殊字符",
                "ph": "X",
                "cat": "cuda",
                "ts": 1000.0,
                "dur": 100.0,
                "tid": "CUDA API 0",
                "pid": "Device 0",
                "args": {"description": "Test with émojis 🚀 and ñoño"},
            }
        ]

        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            # Should handle special characters without issues
            display_nsys_json_in_notebook(special_json)

            mock_display.assert_called_once()
            mock_html.assert_called_once()

    def test_unique_id_generation(self, sample_nsys_json):
        """Test that unique IDs are generated for each invocation."""
        mock_display = Mock()
        mock_html = Mock()

        with patch.dict(
            "sys.modules",
            {
                "IPython.display": MagicMock(display=mock_display, HTML=mock_html),
            },
        ):
            # Call the function twice
            display_nsys_json_in_notebook(sample_nsys_json)
            display_nsys_json_in_notebook(sample_nsys_json)

            # Should have been called twice
            assert mock_display.call_count == 2
            assert mock_html.call_count == 2

            # Get the HTML from both calls
            first_html = mock_html.call_args_list[0][0][0]
            second_html = mock_html.call_args_list[1][0][0]

            # Extract unique IDs from both calls
            first_id_match = re.search(r"open-perfetto-([a-f0-9]{8})", first_html)
            second_id_match = re.search(r"open-perfetto-([a-f0-9]{8})", second_html)

            assert first_id_match is not None
            assert second_id_match is not None

            first_id = first_id_match.group(1)
            second_id = second_id_match.group(1)

            # IDs should be different
            assert first_id != second_id

            # Both should be valid 8-character hex strings
            assert len(first_id) == 8
            assert len(second_id) == 8
            assert all(c in "0123456789abcdef" for c in first_id)
            assert all(c in "0123456789abcdef" for c in second_id)

    def test_nsys_file_not_found_error(self):
        """Test error handling when SQLite file doesn't exist."""
        nonexistent = "nonexistent.sqlite"

        with pytest.raises(Exception):
            display_nsys_sqlite_file_in_notebook(nonexistent)

    def test_nsys_invalid_sqlite_file(self, tmp_path):
        """Test error handling when file is not a valid SQLite database."""
        invalid_file = tmp_path / "invalid.sqlite"
        invalid_file.write_text("This is not a SQLite file")

        with pytest.raises(Exception):
            display_nsys_sqlite_file_in_notebook(str(invalid_file))
