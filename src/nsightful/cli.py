"""
Command-line interface for Nsightful.

This module provides the main CLI entry point for converting Nsight output to other formats.
It handles argument parsing, file validation, and output redirection.

Example usage:
    nsightful results.csv                # Output to stdout
    nsightful results.csv -o results.md  # Save to file
"""

import sys
import argparse
from pathlib import Path
from .ncu import convert_ncu_csv_to_flat_markdown


def main() -> None:
    """Main function to handle command line arguments and execute conversion."""
    parser = argparse.ArgumentParser(
        description="Convert NVIDIA Nsight Compute (NCU) CSV output to Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nsightful results.csv                # Output to stdout
  nsightful results.csv -o results.md  # Save to file

Nsight Compute CSV files can be generated using:
  ncu --set full -o MYREPORT ./MYAPPLICATION
  ncu --import MYREPORT.ncu-rep --csv > MYREPORT.csv
        """,
    )

    parser.add_argument("csv_file", help="Path to the NCU CSV file to convert")

    parser.add_argument("-o", "--output", help="Output file path (default: stdout)", type=Path)

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
