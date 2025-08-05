"""
nsightful: Convert [NVIDIA Nsight](https://developer.nvidia.com/tools-overview) reports to other
formats and elegantly display them in Jupyter notebooks.
"""

from .ncu import (
    parse_ncu_csv,
    convert_ncu_csv_to_flat_markdown,
    extract_kernel_name,
    get_sorted_ncu_sections,
    format_numeric_value,
    format_ncu_rule_type,
)

from .notebook import (
    display_ncu_csv_in_notebook,
    display_ncu_csv_file_in_notebook,
    display_nsys_sqlite_in_notebook,
    display_nsys_sqlite_file_in_notebook,
    display_nsys_json_in_notebook,
)

from .nsys import (
    NsysActivityType,
    convert_nsys_sqlite_to_json,
    convert_nsys_time_to_chrome_trace_time,
)

__version__ = "0.1.0"
__author__ = "NVIDIA Corporation"

__all__ = [
    "parse_ncu_csv",
    "convert_ncu_csv_to_flat_markdown",
    "display_ncu_csv_in_notebook",
    "display_ncu_csv_file_in_notebook",
    "display_nsys_sqlite_in_notebook",
    "display_nsys_sqlite_file_in_notebook",
    "display_nsys_json_in_notebook",
    "extract_kernel_name",
    "get_sorted_ncu_sections",
    "format_numeric_value",
    "format_ncu_rule_type",
    "NsysActivityType",
    "convert_nsys_sqlite_to_json",
    "convert_nsys_time_to_chrome_trace_time",
]
