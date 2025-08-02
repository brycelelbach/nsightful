"""
ncu2markdown: Convert [NVIDIA Nsight Compute](https://developer.nvidia.com/nsight-compute) CSV
output to Markdown that can be output to a file or displayed in a tabbed widget in Jupyter notebooks.
"""

from .core import (
    parse_ncu_csv_data,
    convert_ncu_csv_to_flat_markdown,
    extract_kernel_name,
    get_sorted_sections,
    format_numeric_value,
    format_rule_type
)

from .notebook import display_ncu_data_in_notebook

__version__ = "0.1.0"
__author__ = "NVIDIA Corporation"

__all__ = [
    "parse_ncu_csv_data",
    "convert_ncu_csv_to_flat_markdown",
    "display_ncu_data_in_notebook",
    "extract_kernel_name",
    "get_sorted_sections",
    "format_numeric_value",
    "format_rule_type"
]
