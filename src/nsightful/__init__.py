"""
nsightful: Convert [NVIDIA Nsight](https://developer.nvidia.com/tools-overview) reports to other
formats and elegantly display them in Jupyter notebooks.
"""

from .ncu import (
    parse_ncu_csv_data,
    convert_ncu_csv_to_flat_markdown,
    extract_kernel_name,
    get_sorted_ncu_sections,
    format_numeric_value,
    format_ncu_rule_type,
)

from .notebook import display_ncu_report_in_notebook

__version__ = "0.1.0"
__author__ = "NVIDIA Corporation"

__all__ = [
    "parse_ncu_csv_data",
    "convert_ncu_csv_to_flat_markdown",
    "display_ncu_report_in_notebook",
    "extract_kernel_name",
    "get_sorted_ncu_sections",
    "format_numeric_value",
    "format_ncu_rule_type",
]
