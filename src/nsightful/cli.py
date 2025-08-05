"""
Command-line interface for Nsightful.

This module provides the main CLI entry point for converting Nsight output to other formats.
It handles argument parsing, file validation, and output redirection.
"""

import sys
import argparse
import json
import sqlite3
from pathlib import Path
from .ncu import convert_ncu_csv_to_flat_markdown
from .nsys import convert_nsys_sqlite_to_json


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Convert NVIDIA Nsight output to other formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # NCU subcommand
    ncu_parser = subparsers.add_parser(
        'ncu',
        help='Convert Nsight Compute (NCU) CSV output to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nsightful ncu results.csv                # Output to stdout
  nsightful ncu results.csv -o results.md  # Save to file

Nsight Compute CSV files can be generated using:
  ncu --set full -o MYREPORT ./MYAPPLICATION
  ncu --import MYREPORT.ncu-rep --csv > MYREPORT.csv
        """,
    )
    ncu_parser.add_argument("csv_file", help="Path to the NCU CSV file to convert")
    ncu_parser.add_argument("-o", "--output", help="Output file path (default: stdout)", type=Path)

    # Nsys subcommand
    nsys_parser = subparsers.add_parser(
        'nsys',
        help='Convert Nsight Systems sqlite output to Google Chrome Event Trace Format JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nsightful nsys profile.nsys-rep -o profile.json
  nsightful nsys profile.sqlite --activity-type kernel nvtx

Nsight Systems files can be generated using:
  nsys profile -o MYREPORT ./MYAPPLICATION
  nsys export --type sqlite MYREPORT.nsys-rep
        """,
    )
    nsys_parser.add_argument("-f", '--filename', help="Path to the input sqlite file.", required=True)
    nsys_parser.add_argument("-o", "--output", help="Output file name, default to same as input with .json extension.")
    nsys_parser.add_argument("-t", "--activity-type", help="Type of activities shown. Default to all.", default=None, choices=['kernel', 'nvtx', "nvtx-kernel", "cuda-api"], nargs="+")
    nsys_parser.add_argument("--nvtx-event-prefix", help="Filter NVTX events by their names' prefix.", type=str, nargs="*")
    nsys_parser.add_argument("--nvtx-color-scheme", help="""Color scheme for NVTX events.
                                                    Accepts a dict mapping a string to one of chrome tracing colors.
                                                    Events with names containing the string will be colored.
                                                    E.g. {"send": "thread_state_iowait", "recv": "thread_state_iowait", "compute": "thread_state_running"}
                                                    For details of the color scheme, see links in https://github.com/google/perfetto/issues/208
                                                    """, type=json.loads, default={})

    return parser


def handle_ncu_command(args) -> None:
    """Handle the NCU subcommand."""
    csv_file = Path(args.csv_file)

    if not csv_file.exists():
        print(f"Error: File '{csv_file}' not found.", file=sys.stderr)
        sys.exit(1)

    if not csv_file.is_file():
        print(f"Error: '{csv_file}' is not a file.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(csv_file, "r", encoding="utf-8") as ncu_csv:
            markdown_content = convert_ncu_csv_to_flat_markdown(ncu_csv)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as output_file:
                    output_file.write(markdown_content)
            else:
                print(markdown_content)

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied accessing '{csv_file}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: During file processing: {e}", file=sys.stderr)
        sys.exit(1)


def handle_nsys_command(args) -> None:
    """Handle the Nsys subcommand."""
    try:
        conn = sqlite3.connect(args.filename)
        conn.row_factory = sqlite3.Row

        trace_events = convert_nsys_sqlite_to_json(
            conn,
            activities=args.activity_type,
            event_prefix=args.nvtx_event_prefix,
            color_scheme=args.nvtx_color_scheme
        )

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(trace_events, f)
        else:
            json.dump(trace_events, sys.stdout)

    except FileNotFoundError:
        print(f"Error: File '{args.filename}' not found.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied accessing '{args.filename}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: During file processing: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main function to handle command line arguments and execute conversion."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'ncu':
        handle_ncu_command(args)
    elif args.command == 'nsys':
        handle_nsys_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
