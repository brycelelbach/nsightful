"""
Jupyter notebook display functionality for Nsight Compute data.
"""

from typing import Iterable
from .core import (
    parse_ncu_csv_data,
    add_per_section_markdown,
    get_sorted_sections,
    format_rule_type
)


def display_ncu_data_in_notebook(ncu_csv: Iterable[str]) -> None:
    """Display NCU data in a Jupyter notebook with tabs and a kernel selector.

    Args:
        ncu_csv: Iterable object that produces lines of CSV, e.g. a file object.
    """
    try:
        import ipywidgets as widgets
        from IPython.display import display, HTML, Markdown, clear_output
    except ImportError:
        print("Error: ipywidgets and IPython are required for this function.")
        print("Install with: pip install ipywidgets")
        return

    ncu_data = add_per_section_markdown(parse_ncu_csv_data(ncu_csv))

    # Disable nested scrolling in Google Colab because it scrolls past the tabs and selector.
    try:
        from google.colab import output
        output.no_vertical_scroll()
    except ImportError:
        pass

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

    /* Make borders theme-aware too */
    .widget-output, .widget-tab .p-TabBar {
      border-color: var(--jp-border-color2, #ddd) !important;
    }

    /* Fit tab title to the length of text */
    .widget-tab .p-TabBar-tab {
      min-width: auto !important;
      width: auto !important;
      flex: 0 0 auto !important;
    }

    .widget-tab .p-TabBar-tabLabel {
      white-space: nowrap !important;
      text-overflow: clip !important;
      overflow: visible !important;
      padding: 0 0 !important;
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

            sections = ncu_data[selected_kernel]

            if not sections:
                print(f"No sections found for kernel: {selected_kernel}")
                return

            # Create summary tab listing all rules.
            summary_content = []
            summary_content.append("## Summary\n")

            # Extract all rules from all sections in sorted order, grouped by section
            rules_found = False
            for section_name, section_data in get_sorted_sections(sections):
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
                    display(Markdown("## Summary\n\nNo rules found in any section."))

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
