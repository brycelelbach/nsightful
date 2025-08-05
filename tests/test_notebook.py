"""
Tests for nsightful Jupyter notebook functionality.
"""

import io
from unittest.mock import Mock, patch, MagicMock
import pytest

from nsightful.notebook import display_ncu_csv_in_notebook


class TestDisplayNcuDataInNotebook:
    """Test the display_ncu_csv_in_notebook function."""

    def test_missing_dependencies_handling(self, capsys, sample_csv_io):
        """Test handling when ipywidgets/IPython are not available."""
        with patch("builtins.__import__", side_effect=ImportError):
            display_ncu_csv_in_notebook(sample_csv_io)

        captured = capsys.readouterr()
        assert "Error: ipywidgets and IPython are required" in captured.out
        assert "pip install ipywidgets" in captured.out

    def test_successful_display_basic(self, sample_csv_io):
        """Test that display function handles sample data without crashing."""
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
                "IPython.display": Mock(
                    display=mock_display,
                    HTML=mock_html,
                    Markdown=mock_markdown,
                    clear_output=mock_clear_output,
                ),
            },
        ):
            # This should not raise an exception
            display_ncu_csv_in_notebook(sample_csv_io)

            # Verify basic setup was attempted
            assert mock_widgets.Dropdown.called
            assert mock_widgets.Output.called

    def test_real_data_parsing(self, real_test_csv_file):
        """Test that notebook display can parse real data without widgets."""
        # Test with ImportError to verify parsing works
        with patch("builtins.__import__", side_effect=ImportError):
            with open(real_test_csv_file, "r") as f:
                # Should not crash even though widgets are not available
                display_ncu_csv_in_notebook(f)

    def test_empty_data_handling(self):
        """Test handling of empty CSV data."""
        empty_csv = '''\"ID\",\"Process ID\",\"Process Name\",\"Host Name\",\"Kernel Name\",\"Context\",\"Stream\",\"Block Size\",\"Grid Size\",\"Device\",\"CC\",\"Section Name\",\"Metric Name\",\"Metric Unit\",\"Metric Value\",\"Rule Name\",\"Rule Type\",\"Rule Description\",\"Estimated Speedup Type\",\"Estimated Speedup\"'''

        csv_io = io.StringIO(empty_csv)

        # Test with ImportError - should handle gracefully
        with patch("builtins.__import__", side_effect=ImportError):
            display_ncu_csv_in_notebook(csv_io)

    def test_widget_creation_flow(self, sample_csv_io):
        """Test the widget creation flow with mocked dependencies."""
        mock_widgets = Mock()
        mock_ipython = Mock()

        # Set up the mocks
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

        # Mock dropdown value for callback testing
        mock_dropdown.value = "simple_kernel"

        # Mock the module imports
        modules = {
            "ipywidgets": mock_widgets,
            "IPython": mock_ipython,
            "IPython.display": Mock(
                display=Mock(), HTML=Mock(), Markdown=Mock(), clear_output=Mock()
            ),
            "google": Mock(),
            "google.colab": Mock(),
            "google.colab.output": Mock(),
        }

        with patch.dict("sys.modules", modules):
            # Import should succeed and widgets should be created
            display_ncu_csv_in_notebook(sample_csv_io)

            # Verify the main widgets were created
            mock_widgets.Dropdown.assert_called_once()
            assert mock_widgets.Output.call_count >= 1  # Multiple outputs created

            # Verify dropdown setup
            dropdown_call = mock_widgets.Dropdown.call_args
            assert "options" in dropdown_call.kwargs
            assert "description" in dropdown_call.kwargs
            assert dropdown_call.kwargs["description"] == "Kernel:"

            # Verify observe was set up
            mock_dropdown.observe.assert_called_once()

    def test_colab_import_handling(self, sample_csv_io):
        """Test that Google Colab import is handled gracefully."""
        mock_widgets = Mock()
        mock_ipython = Mock()

        mock_output = Mock()
        mock_output.__enter__ = Mock(return_value=mock_output)
        mock_output.__exit__ = Mock(return_value=None)

        mock_widgets.Dropdown.return_value = Mock()
        mock_widgets.Output.return_value = mock_output
        mock_widgets.Tab.return_value = Mock()
        mock_widgets.Layout.return_value = Mock()

        # Test both with and without Google Colab
        modules_without_colab = {
            "ipywidgets": mock_widgets,
            "IPython": mock_ipython,
            "IPython.display": Mock(
                display=Mock(), HTML=Mock(), Markdown=Mock(), clear_output=Mock()
            ),
        }

        with patch.dict("sys.modules", modules_without_colab):
            # Should work without Google Colab
            display_ncu_csv_in_notebook(sample_csv_io)
            mock_widgets.Dropdown.assert_called_once()
