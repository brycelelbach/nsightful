"""
Core functionality for parsing and converting Nsight Compute reports.
"""

import csv
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Iterable, Union

# Mapping from raw NCU CSV section names to canonical user-facing names.
# Order matters: canonical names will appear in output in the order they appear here.
# All entries for a canonical name must be grouped together.
NCU_SECTION_MAPPINGS = {
    # Speed Of Light variations (canonical: Speed Of Light)
    "GPU Speed Of Light Throughput": "Speed Of Light",
    "SpeedOfLight": "Speed Of Light",
    "SpeedOfLight_RooflineChart": "Speed Of Light",
    # Memory Workload variations (canonical: Memory Workload)
    "Memory Workload Analysis": "Memory Workload",
    "MemoryWorkloadAnalysis": "Memory Workload",
    "MemoryWorkloadAnalysis_Chart": "Memory Workload",
    "MemoryWorkloadAnalysis_Tables": "Memory Workload",
    # Compute Workload variations (canonical: Compute Workload)
    "Compute Workload Analysis": "Compute Workload",
    "ComputeWorkloadAnalysis": "Compute Workload",
    "GPU and Memory Workload Distribution": "Compute & Memory Distribution",
    # Scheduler variations (canonical: Scheduler)
    "Scheduler Statistics": "Scheduler",
    "SchedulerStats": "Scheduler",
    # Warp State variations (canonical: Warp State)
    "Warp State Statistics": "Warp State",
    "WarpStateStats": "Warp State",
    "Instruction Statistics": "Instruction",
    "Launch Statistics": "Launch",
    "PM Sampling": "PM Sampling",
    "Occupancy": "Occupancy",
    # Source Counters variations (canonical: Source Counter)
    "Source Counters": "Source Counters",
    "SourceCounters": "Source Counters",
}


def get_sorted_ncu_sections(ncu_sections: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Return the Nsight Compute sections sorted according to our canonical output order.

    Args:
        ncu_sections (dict): Dictionary of section_name: section_data

    Returns:
        list: List of (section_name, section_data) tuples in sorted order
    """
    # Get canonical section order from NCU_SECTION_MAPPINGS values.
    # dict.fromkeys preserves insertion order & removes duplicates; python has no unique operation.
    section_order = list(dict.fromkeys(NCU_SECTION_MAPPINGS.values()))

    # Sort sections, putting known sections first in order, then others
    sorted_sections = []
    remaining_sections = dict(ncu_sections)

    for section in section_order:
        if section in remaining_sections:
            sorted_sections.append((section, remaining_sections[section]))
            del remaining_sections[section]

    # Add any remaining sections
    for section, data in remaining_sections.items():
        sorted_sections.append((section, data))

    return sorted_sections


def extract_kernel_name(full_kernel_name: str) -> str:
    """Extract the base kernel name from the full template name."""
    # Extract everything before the first '[' or '('
    match = re.match(r"^([^[\(]+)", full_kernel_name)
    if match:
        return match.group(1).strip()
    return full_kernel_name


def format_numeric_value(value_str: str) -> str:
    """Format numeric values for better readability."""
    if not value_str:
        return ""

    # Handle comma-separated numbers
    if "," in value_str:
        try:
            # Remove commas and check if it's a float
            clean_value = value_str.replace(",", "")
            float_val = float(clean_value)

            # If it's a large integer, add commas back
            if float_val.is_integer() and abs(float_val) >= 1000:
                return f"{int(float_val):,}"
            elif abs(float_val) >= 1000:
                return f"{float_val:,.2f}"
            else:
                return clean_value
        except ValueError:
            return value_str

    return value_str


def format_ncu_rule_type(rule_type: str) -> str:
    """Format Nsight Compute rule type with appropriate emoji and styling."""
    if rule_type == "OPT":
        return "🔧 **OPTIMIZATION**"
    elif rule_type == "WRN":
        return "⚠️ **WARNING**"
    elif rule_type == "INF":
        return "ℹ️ **INFO**"
    else:
        return f"**{rule_type}**"


def parse_ncu_csv(
    ncu_csv: Iterable[str],
) -> Dict[str, Dict[str, Dict[str, Union[Dict[str, Dict[str, str]], List[Dict[str, str]]]]]]:
    """Parse Nsight Compute CSV and return structured data.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.

    Returns:
        dict: {kernel_name: {section_name: {'Metrics': {}, 'Rules': []}}}
    """
    kernels: Dict[
        str, Dict[str, Dict[str, Union[Dict[str, Dict[str, str]], List[Dict[str, str]]]]]
    ] = defaultdict(lambda: defaultdict(lambda: {"Metrics": {}, "Rules": []}))

    reader = csv.DictReader(ncu_csv)
    for row in reader:
        full_kernel_name = row["Kernel Name"]
        kernel_name = extract_kernel_name(full_kernel_name)
        section_name = NCU_SECTION_MAPPINGS.get(row["Section Name"], row["Section Name"])

        # Skip rows without section names
        if not section_name:
            continue

        # If this row has metric data
        if row["Metric Name"].strip():
            metric_name = row["Metric Name"].strip()
            metric = {
                "Name": metric_name,
                "Unit": row["Metric Unit"].strip(),
                "Value": format_numeric_value(row["Metric Value"].strip()),
            }
            metrics_dict = kernels[kernel_name][section_name]["Metrics"]
            if isinstance(metrics_dict, dict):
                metrics_dict[metric_name] = metric

        # If this row has rule data
        if row["Rule Name"].strip():
            rule = {
                "Name": row["Rule Name"].strip(),
                "Type": row["Rule Type"].strip(),
                "Description": row["Rule Description"].strip(),
                "Speedup_type": row["Estimated Speedup Type"].strip(),
                "Speedup": row["Estimated Speedup"].strip(),
            }
            rules_list = kernels[kernel_name][section_name]["Rules"]
            if isinstance(rules_list, list):
                rules_list.append(rule)

    return dict(kernels)


def add_per_section_ncu_markdown(
    ncu_dict: Dict[
        str, Dict[str, Dict[str, Union[Dict[str, Dict[str, str]], List[Dict[str, str]]]]]
    ],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Add per-section Markdown to the parsed Nsight Compute data.

    Args:
        ncu_dict (dict): Data structure from parse_ncu_csv()
                         Format: {kernel_name: {section_name: {'Metrics': {}, 'Rules': []}}}

    Returns:
        dict: {kernel_name: {section_name: {'Metrics': {}, 'Rules': [], 'Markdown': str}}}
    """
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for kernel_name, sections in ncu_dict.items():
        result[kernel_name] = {}
        for section_name, data in sections.items():
            section_data: Dict[str, Any] = {"Metrics": data["Metrics"], "Rules": data["Rules"]}

            markdown_lines = []

            # Section heading (h2)
            markdown_lines.append(f"## {section_name}\n")

            # Metrics table
            metrics_data = section_data["Metrics"]
            if isinstance(metrics_data, dict) and metrics_data:
                markdown_lines.append("| Metric Name | Metric Unit | Metric Value |")
                markdown_lines.append("|-------------|-------------|--------------|")
                for metric in metrics_data.values():
                    unit = metric["Unit"] if metric["Unit"] else ""
                    value = metric["Value"] if metric["Value"] else ""
                    markdown_lines.append(f"| {metric['Name']} | {unit} | {value} |")
                markdown_lines.append("")

            # Rules/recommendations
            rules_data = section_data["Rules"]
            if isinstance(rules_data, list):
                for rule in rules_data:
                    prefix = format_ncu_rule_type(rule["Type"])
                    description = rule["Description"]

                    markdown_lines.append(f"{prefix}: {description}")

                    if rule["Speedup"] and rule["Speedup_type"]:
                        speedup_text = (
                            f"*Estimated Speedup ({rule['Speedup_type']}): {rule['Speedup']}%*"
                        )
                        markdown_lines.append(speedup_text)

                    markdown_lines.append("")

            # Add the markdown content to the existing section data
            section_data["Markdown"] = "\n".join(markdown_lines)
            result[kernel_name][section_name] = section_data

    return result


def convert_ncu_csv_to_flat_markdown(ncu_csv: Iterable[str]) -> str:
    """Convert NCU CSV to a flat Markdown format.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.

    Returns:
        str: Single markdown string ready for printing
    """
    nested_markdown = add_per_section_ncu_markdown(parse_ncu_csv(ncu_csv))
    markdown_lines = []

    for kernel_name, sections in nested_markdown.items():
        # Kernel heading (h1)
        markdown_lines.append(f"# {kernel_name}\n")

        if not sections:
            markdown_lines.append(f"No sections found for kernel: {kernel_name}")
            continue

        # Add each section's markdown in sorted order
        for section_name, section_data in get_sorted_ncu_sections(sections):
            markdown_lines.append(section_data["Markdown"])

        markdown_lines.append("---\n")  # Add separator between kernels

    return "\n".join(markdown_lines)
