#!/usr/bin/env python3
"""
NCU CSV to Markdown Converter

Convert NVIDIA Nsight Compute (NCU) CSV output to a readable Markdown format which
can be output on the command line or displayed in a tabbed widget in a Jupyter
notebook.

You can capture NCU CSV output by running::

    ncu --set full -o MYREPORT ./MYBINARY
    ncu --import MYREPORT.ncu-rep --csv > MYREPORT.csv
"""

import csv
import sys
import re
from collections import defaultdict


def extract_kernel_name(full_kernel_name):
    """Extract the base kernel name from the full template name."""
    # Extract everything before the first '[' or '('
    match = re.match(r'^([^[\(]+)', full_kernel_name)
    if match:
        return match.group(1).strip()
    return full_kernel_name


# Combined section mappings and order - list of tuples (variation, canonical).
# Order matters: canonical names will be sorted in the order they first appear.
SECTION_MAPPINGS = [
    # Speed Of Light variations (canonical: Speed Of Light)
    ('GPU Speed Of Light Throughput', 'Speed Of Light'),
    ('SpeedOfLight', 'Speed Of Light'),
    ('SpeedOfLight_RooflineChart', 'Speed Of Light'),

    # Memory Workload variations (canonical: Memory Workload)
    ('Memory Workload Analysis', 'Memory Workload'),
    ('MemoryWorkloadAnalysis', 'Memory Workload'),
    ('MemoryWorkloadAnalysis_Chart', 'Memory Workload'),
    ('MemoryWorkloadAnalysis_Tables', 'Memory Workload'),

    # Compute Workload variations (canonical: Compute Workload)
    ('Compute Workload Analysis', 'Compute Workload'),
    ('ComputeWorkloadAnalysis', 'Compute Workload'),

    ('GPU and Memory Workload Distribution', 'Compute & Memory Distribution'),

    # Scheduler variations (canonical: Scheduler)
    ('Scheduler Statistics', 'Scheduler'),
    ('SchedulerStats', 'Scheduler'),

    # Warp State variations (canonical: Warp State)
    ('Warp State Statistics', 'Warp State'),
    ('WarpStateStats', 'Warp State'),

    ('Instruction Statistics', 'Instruction'),

    ('Launch Statistics', 'Launch'),

    ('PM Sampling', 'PM Sampling'),

    ('Occupancy', 'Occupancy'),

    # Source Counters variations (canonical: Branching)
    ('Source Counters', 'Branching'),
    ('SourceCounters', 'Branching'),
]


def normalize_section_name(section_name):
    """Normalize section names to merge similar sections."""
    if not section_name:
        return section_name

    section = section_name.strip()

    # Create mapping dict from the combined structure
    section_mappings = dict(SECTION_MAPPINGS)

    # Return the canonical name if we have a mapping, otherwise return original
    return section_mappings.get(section, section)


def get_sorted_sections(sections):
    """Get sections sorted according to typical NCU output order.

    Args:
        sections (dict): Dictionary of section_name: section_data

    Returns:
        list: List of (section_name, section_data) tuples in sorted order
    """
    # Extract canonical names in order from SECTION_MAPPINGS (preserving order, removing duplicates)
    seen_canonical = set()
    section_order = []
    for _, canonical_name in SECTION_MAPPINGS:
        if canonical_name not in seen_canonical:
            section_order.append(canonical_name)
            seen_canonical.add(canonical_name)

    # Sort sections, putting known sections first in order, then others
    sorted_sections = []
    remaining_sections = dict(sections)

    for section in section_order:
        if section in remaining_sections:
            sorted_sections.append((section, remaining_sections[section]))
            del remaining_sections[section]

    # Add any remaining sections
    for section, data in remaining_sections.items():
        sorted_sections.append((section, data))

    return sorted_sections


def format_numeric_value(value_str):
    """Format numeric values for better readability."""
    if not value_str:
        return ""

    # Handle comma-separated numbers
    if ',' in value_str:
        try:
            # Remove commas and check if it's a float
            clean_value = value_str.replace(',', '')
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


def format_rule_type(rule_type):
    """Format rule type with appropriate emoji and styling."""
    if rule_type == 'OPT':
        return "🔧 **OPTIMIZATION**"
    elif rule_type == 'WRN':
        return "⚠️ **WARNING**"
    elif rule_type == 'INF':
        return "ℹ️ **INFO**"
    else:
        return f"**{rule_type}**"


def parse_ncu_csv_data(ncu_csv):
    """Parse NCU CSV and return structured data.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.

    Returns:
        dict: {kernel_name: {section_name: {'metrics': [], 'rules': []}}}
    """
    # Data structure: kernel_name -> section_name -> {'metrics': [], 'rules': []}
    kernels = defaultdict(lambda: defaultdict(lambda: {'metrics': [], 'rules': []}))

    reader = csv.DictReader(ncu_csv)
    for row in reader:
        full_kernel_name = row['Kernel Name']
        kernel_name = extract_kernel_name(full_kernel_name)
        section_name = normalize_section_name(row['Section Name'])

        # Skip rows without section names
        if not section_name:
            continue

        # If this row has metric data
        if row['Metric Name'].strip():
            metric = {
                'name': row['Metric Name'].strip(),
                'unit': row['Metric Unit'].strip(),
                'value': format_numeric_value(row['Metric Value'].strip())
            }
            kernels[kernel_name][section_name]['metrics'].append(metric)

        # If this row has rule data
        if row['Rule Name'].strip():
            rule = {
                'name': row['Rule Name'].strip(),
                'type': row['Rule Type'].strip(),
                'description': row['Rule Description'].strip(),
                'speedup_type': row['Estimated Speedup Type'].strip(),
                'speedup': row['Estimated Speedup'].strip()
            }
            kernels[kernel_name][section_name]['rules'].append(rule)

    return kernels


def add_per_section_markdown(ncu_data):
    """Add per-section Markdown to the parsed NCU data.

    Args:
        ncu_data (dict): Data structure from parse_ncu_csv_data()
                         Format: {kernel_name: {section_name: {'metrics': [], 'rules': []}}}

    Returns:
        dict: {kernel_name: {section_name: {'metrics': [], 'rules': [], 'markdown': str}}}
    """
    for kernel_name, sections in ncu_data.items():
        for section_name, data in sections.items():
            markdown_lines = []

            # Section heading (h2)
            markdown_lines.append(f"## {section_name}\n")

            # Metrics table
            if data['metrics']:
                markdown_lines.append("| Metric Name | Metric Unit | Metric Value |")
                markdown_lines.append("|-------------|-------------|--------------|")
                for metric in data['metrics']:
                    unit = metric['unit'] if metric['unit'] else ''
                    value = metric['value'] if metric['value'] else ''
                    markdown_lines.append(f"| {metric['name']} | {unit} | {value} |")
                markdown_lines.append("")

            # Rules/recommendations
            for rule in data['rules']:
                prefix = format_rule_type(rule['type'])
                description = rule['description']

                markdown_lines.append(f"{prefix}: {description}")

                if rule['speedup'] and rule['speedup_type']:
                    speedup_text = f"*Estimated Speedup ({rule['speedup_type']}): {rule['speedup']}%*"
                    markdown_lines.append(speedup_text)

                markdown_lines.append("")

            # Add the markdown content to the existing section data
            data['markdown'] = "\n".join(markdown_lines)

    return ncu_data


def convert_ncu_csv_to_flat_markdown(ncu_csv):
    """COnvert NCU CSV to a flat Markdown format.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.

    Returns:
        str: Single markdown string ready for printing
    """
    nested_markdown = parse_ncu_csv_to_nested_markdown(ncu_csv)
    markdown_lines = []

    for kernel_name, sections in nested_markdown.items():
        # Kernel heading (h1)
        markdown_lines.append(f"# {kernel_name}\n")

        # Add each section's markdown in sorted order
        for section_name, section_markdown in get_sorted_sections(sections):
            markdown_lines.append(section_markdown)

        markdown_lines.append("---\n")  # Add separator between kernels

    return "\n".join(markdown_lines)


def display_ncu_data_in_notebook(ncu_csv):
    """Display NCU data in a Jupyter notebook with tabs and a kernel selector.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.

    Args:
        ncu_data (dict): Nested NCU data with per-section markdown from add_per_section_markdown(parse_ncu_csv_data(...))
                         Format: {kernel_name: {section_name: {'metrics': [], 'rules': [], 'markdown': str}}}
    """
    try:
        import ipywidgets as widgets
        from IPython.display import display, HTML, Markdown, clear_output
    except ImportError:
        print("Error: ipywidgets and IPython are required for this function.")
        print("Install with: pip install ipywidgets")
        return

    ncu_data = add_per_section_markdown(parse_ncu_csv_data(ncu_csv))

    # Ensure text in the widget respects dark/light mode.
    display(HTML("""
    <style>
    /* Use JupyterLab theme variables when available */
    .widget-tab .p-TabBar .p-TabBar-tabLabel {
      color: var(--jp-ui-font-color1, inherit);
    }
    .widget-tab .p-TabBar-tab.p-mod-current .p-TabBar-tabLabel {
      color: var(--jp-ui-font-color0, inherit);
    }

    /* Fallback for classic notebook / VS Code: follow OS theme */
    @media (prefers-color-scheme: dark) {
      .widget-tab .p-TabBar .p-TabBar-tabLabel { color: #eee; }
      .widget-tab .p-TabBar-tab.p-mod-current .p-TabBar-tabLabel { color: #fff; }
    }
    @media (prefers-color-scheme: light) {
      .widget-tab .p-TabBar .p-TabBar-tabLabel { color: #111; }
      .widget-tab .p-TabBar-tab.p-mod-current .p-TabBar-tabLabel { color: #000; }
    }

    /* Optional: make borders theme-aware too */
    .widget-output, .widget-tab .p-TabBar {
      border-color: var(--jp-border-color2, #ddd) !important;
    }
    </style>
    """))

    # Get list of kernel names
    kernel_names = list(ncu_data.keys())

    # Create dropdown for kernel selection
    kernel_dropdown = widgets.Dropdown(
        options=kernel_names,
        value=kernel_names[0] if kernel_names else None,
        description='Kernel:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='400px')
    )

    # Create output widget for displaying tabs
    output_area = widgets.Output()

    def update_tabs(change):
        """Update the tabs when kernel selection changes."""
        selected_kernel = change['new']

        with output_area:
            clear_output(wait=True)

            if selected_kernel not in ncu_data:
                print(f"No data found for kernel: {selected_kernel}")
                return

            kernel_data = ncu_data[selected_kernel]

            if not kernel_data:
                print(f"No sections found for kernel: {selected_kernel}")
                return

            # Create summary tab listing all rules.
            summary_content = []
            summary_content.append("## Summary\n")

            # Extract all rules from all sections in sorted order, grouped by section
            rules_found = False
            for section_name, section_data in get_sorted_sections(kernel_data):
                if section_data['rules']:  # Only add section header if there are rules
                    rules_found = True

                    # Add section header
                    summary_content.append(f"### {section_name}\n")

                    # Add all rules from this section
                    for rule in section_data['rules']:
                        # Format rule type with emoji
                        prefix = format_rule_type(rule['type'])

                        # Add rule description
                        summary_content.append(f"{prefix}: {rule['description']}")

                        # Add speedup information if available
                        if rule['speedup'] and rule['speedup_type']:
                            summary_content.append(f"*Estimated Speedup ({rule['speedup_type']}): {rule['speedup']}%*")

                        summary_content.append("")  # Add blank line after each rule

            # Create summary tab
            summary_output = widgets.Output()
            with summary_output:
                if rules_found:
                    display(Markdown("\n".join(summary_content)))
                else:
                    display(Markdown("## Summary - All Rules\n\nNo rules found in any section."))

            # Create tabs for each section in sorted order
            sorted_sections = get_sorted_sections(kernel_data)
            tab_children = [summary_output]  # Summary tab first
            tab_titles = ["Summary"]  # Summary tab title first

            for section_name, section_data in sorted_sections:
                # Create output widget for each tab
                section_output = widgets.Output()

                with section_output:
                    # Display the markdown content for this section
                    if 'markdown' in section_data and section_data['markdown'].strip():
                        display(Markdown(section_data['markdown']))
                    else:
                        print(f"No content available for section: {section_name}")

                tab_children.append(section_output)
                tab_titles.append(section_name)

            # Create the Tab widget
            tabs = widgets.Tab(children=tab_children)

            # Set tab titles
            for i, title in enumerate(tab_titles):
                tabs.set_title(i, title)

            # Display kernel title and tabs
            display(Markdown(f"# {selected_kernel}"))
            display(tabs)

    # Set up the initial display
    kernel_dropdown.observe(update_tabs, names='value')

    # Display the dropdown
    display(kernel_dropdown)
    display(output_area)

    # Trigger initial display
    update_tabs({'new': kernel_dropdown.value})


def main():
    """Main function to handle command line arguments and execute conversion."""
    if len(sys.argv) != 2:
        print("Usage: python ncu2markdown.py <csv_file>", file=sys.stderr)
        print("\nConverts NCU CSV output to readable Markdown format.", file=sys.stderr)
        print("Example: python ncu2markdown.py results.csv > results.md", file=sys.stderr)
        sys.exit(1)

    ncu_csv_file = sys.argv[1]

    try:
        with open(ncu_csv_file, 'r', encoding='utf-8') as ncu_csv:
            markdown_content = convert_ncu_csv_to_flat_markdown(ncu_csv)
            print(markdown_content)
    except FileNotFoundError:
        print(f"Error: File '{ncu_csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
