"""
Jupyter notebook display functionality for Nsight Compute data.
"""

import base64
import sqlite3
import csv
import json
import uuid
from typing import Iterable, Dict, Any, Optional, List
from .ncu import (
    parse_ncu_csv,
    add_per_section_ncu_markdown,
    get_sorted_ncu_sections,
    format_ncu_rule_type,
)
from .nsys import convert_nsys_sqlite_to_json


def display_ncu_csv_file_in_notebook(ncu_file: str) -> None:
    with open(ncu_file, "r") as f:
        display_ncu_csv_in_notebook(f)


def display_ncu_csv_in_notebook(ncu_csv: Iterable[str]) -> None:
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

    ncu_dict = add_per_section_ncu_markdown(parse_ncu_csv(ncu_csv))

    # Disable nested scrolling in Google Colab because it scrolls past the tabs and selector.
    try:
        from google.colab import output

        output.no_vertical_scroll()
    except ImportError:
        pass

    # Ensure text in the widget respects dark/light mode.
    display(
        HTML(
            """
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
    """
        )
    )

    # Get list of kernel names
    kernel_names = list(ncu_dict.keys())

    # Create dropdown for kernel selection
    kernel_dropdown = widgets.Dropdown(
        options=kernel_names,
        value=kernel_names[0] if kernel_names else None,
        description="Kernel:",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="400px"),
    )

    # Create output widget for displaying tabs
    output_area = widgets.Output()

    def update_tabs(change: Dict[str, Any]) -> None:
        """Update the tabs when kernel selection changes."""
        selected_kernel = change["new"]

        with output_area:
            clear_output(wait=True)

            if selected_kernel not in ncu_dict:
                print(f"No data found for kernel: {selected_kernel}")
                return

            sections = ncu_dict[selected_kernel]

            if not sections:
                print(f"No sections found for kernel: {selected_kernel}")
                return

            # Create summary tab listing all rules.
            summary_content = []
            summary_content.append("## Summary\n")

            # Extract all rules from all sections in sorted order, grouped by section
            rules_found = False
            for section_name, section_data in get_sorted_ncu_sections(sections):
                if section_data["Rules"]:  # Only add section header if there are rules
                    rules_found = True

                    # Add section header
                    summary_content.append(f"### {section_name}\n")

                    # Add all rules from this section
                    rules_data = section_data["Rules"]
                    if isinstance(rules_data, list):
                        for rule in rules_data:
                            # Format rule type with emoji
                            prefix = format_ncu_rule_type(rule["Type"])

                            # Add rule description
                            summary_content.append(f"{prefix}: {rule['Description']}")

                            # Add speedup information if available
                            if rule["Speedup"] and rule["Speedup_type"]:
                                summary_content.append(
                                    f"*Estimated Speedup ({rule['Speedup_type']}): {rule['Speedup']}%*"
                                )

                            summary_content.append("")  # Add blank line after each rule

            # Create summary tab
            summary_output = widgets.Output()
            with summary_output:
                if rules_found:
                    display(Markdown("\n".join(summary_content)))
                else:
                    display(Markdown("## Summary\n\nNo rules found in any section."))

            # Create tabs for each section in sorted order
            sorted_sections = get_sorted_ncu_sections(sections)
            tab_children = [summary_output]  # Summary tab first
            tab_titles = ["Summary"]  # Summary tab title first

            for section_name, section_data in sorted_sections:
                # Create output widget for each tab
                section_output = widgets.Output()

                with section_output:
                    # Display the markdown content for this section
                    if "Markdown" in section_data and section_data["Markdown"].strip():
                        display(Markdown(section_data["Markdown"]))
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
    kernel_dropdown.observe(update_tabs, names="value")

    # Display the dropdown
    display(kernel_dropdown)
    display(output_area)

    # Trigger initial display
    update_tabs({"new": kernel_dropdown.value})


def display_nsys_sqlite_file_in_notebook(nsys_file: str, title: str = "Nsight Systems") -> None:
    from pathlib import Path

    # Check if file exists before attempting to connect
    if not Path(nsys_file).exists():
        raise FileNotFoundError(f"SQLite file '{nsys_file}' not found")

    conn = sqlite3.connect(nsys_file)
    conn.row_factory = sqlite3.Row

    nsys_json = convert_nsys_sqlite_to_json(conn)

    display_nsys_json_in_notebook(nsys_json, title, nsys_file)


def display_nsys_sqlite_in_notebook(
    nsys_sqlite: sqlite3.Connection, title: str = "Nsight Systems", filename: str = "nsys.json"
) -> None:
    nsys_json = convert_nsys_sqlite_to_json(nsys_sqlite)

    display_nsys_json_in_notebook(nsys_json, title, filename)


def display_nsys_json_in_notebook(
    nsys_json: List[Dict[str, Any]], title: str = "Nsight Systems", filename: str = "nsys.json"
) -> None:
    try:
        from IPython.display import HTML, display
    except ImportError:
        print("Error: ipywidgets and IPython are required for this function.")
        print("Install with: pip install ipywidgets")
        return

    # Generate a unique identifier for this invocation to avoid conflicts
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]

    # Convert the list to JSON string and then to bytes for base64 encoding
    json_str = json.dumps(nsys_json)
    json_bytes = json_str.encode("utf-8")
    b64 = base64.b64encode(json_bytes).decode("ascii")

    html = f"""
    <button id="open-perfetto-{unique_id}" style="padding:8px 12px;font-size:14px">Open in Perfetto</button>
    <script>
    (() => {{
    const TITLE_{unique_id}     = {title!r};
    const FILE_NAME_{unique_id} = {filename!r};
    const B64_{unique_id}       = {b64!r};

    function b64ToArrayBuffer_{unique_id}(b64) {{
        const binary = atob(b64);
        const len = binary.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; ++i) bytes[i] = binary.charCodeAt(i);
        return bytes.buffer;
    }}

    async function openPerfetto_{unique_id}() {{
        const ui = window.open('https://ui.perfetto.dev/#!/');
        if (!ui) {{ alert('Popup blocked. Allow popups for this page and click again.'); return; }}

        // Perfetto readiness handshake: PING until we receive PONG
        await new Promise((resolve, reject) => {{
        const onMsg = (e) => {{
            if (e.source === ui && e.data === 'PONG') {{
            window.removeEventListener('message', onMsg);
            clearInterval(pinger);
            resolve();
            }}
        }};
        window.addEventListener('message', onMsg);
        const pinger = setInterval(() => {{ try {{ ui.postMessage('PING', '*'); }} catch (_e) {{}} }}, 250);
        setTimeout(() => {{ clearInterval(pinger); window.removeEventListener('message', onMsg); reject(); }}, 20000);
        }}).catch(() => {{ alert('Perfetto UI did not respond. Try again.'); return; }});

        ui.postMessage({{
        perfetto: {{
            buffer: b64ToArrayBuffer_{unique_id}(B64_{unique_id}),
            title: TITLE_{unique_id},
            fileName: FILE_NAME_{unique_id}
            // No URL here; the Share button won't generate a link without one.
        }}
        }}, '*');
    }}

    document.getElementById('open-perfetto-{unique_id}').addEventListener('click', openPerfetto_{unique_id});
    }})();
    </script>
    """
    display(HTML(html))
