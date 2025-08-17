# Nsightful

[![Apache 2.0 with LLVM exceptions](https://img.shields.io/badge/license-Apache%202.0%20with%20LLVM%20exceptions-blue.svg)](LICENSE)
[![Tests](https://github.com/brycelelbach/nsightful/actions/workflows/test.yml/badge.svg)](https://github.com/brycelelbach/nsightful/actions/workflows/test.yml)

A Python package for converting [NVIDIA Nsight Compute (NCU)](https://developer.nvidia.com/nsight-compute)
and [NVIDIA Nsight Systems (NSYS)](https://developer.nvidia.com/nsight-systems) profile reports to
other formats and elegantly displaying them in Jupyter notebooks and other web-based no-install
tools.

In a nutshell, `nsightful` contains:
- Nsight Compute CSV -> Python dicts, Markdown.
- Nsight Systems SQLite -> [Google Chrome Trace Event Format](https://perfetto.dev/docs/getting-started/other-formats#chrome-json-format) JSON.
- Command line tools for converting Nsight Compute and Nsight Systems reports to those formats.
- Jupyter notebook widget for displaying Nsight Compute and Nsight Systems reports.

## Installation

If you just need the command line tool:

```bash
pip install git+https://github.com/brycelelbach/nsightful.git
```

If you want to use the Jupyter notebook widgets:

```bash
pip install "nsightful[notebook] @ git+https://github.com/brycelelbach/nsightful.git"
```

## Quick Start

### Nsight Compute (NCU)

#### Generating NCU CSV Data

First, you need to generate NCU CSV data from your CUDA application:

```bash
# Profile your application
ncu --set full -o myreport ./myapplication

# Export to CSV
ncu --import myreport.ncu-rep --csv > myreport.csv

# Convert CSV to Markdown (output to a file)
nsightful myreport.csv -o myreport.md
```

#### NCU Python Conversion API

```python
import nsightful

# Convert CSV file to Markdown string
with open('myreport.csv', 'r') as f:
    markdown_content = nsightful.convert_ncu_csv_to_flat_markdown(f)
    print(markdown_content)

# Parse structured data for custom processing
with open('myreport.csv', 'r') as f:
    ncu_data = nsightful.parse_ncu_csv(f)
    # ncu_data is a nested dictionary with kernel -> section -> metrics/rules
```

#### NCU Jupyter Notebook Widget

Nsightful provides a function to display NCU data in a Jupyter notebook widget, reminiscent of the
Nsight Compute GUI.
This widget has:
- A kernel selector dropdown.
- A summary tab showing all Nsight recommendations and advisories.
- One detailed tab for each Nsight compute section.

If you have an existing report file or use the Nsight JupyterLab extension to run a cell under the
profile and collect a report, then you can display it with nsightful:

```python
!pip install "nsightful[notebook] @ git+https://github.com/brycelelbach/nsightful.git"
```

```python
import nsightful

nsightful.display_ncu_csv_file_in_notebook('myreport.csv')
```

or

```python
import nsightful

with open('myreport.csv', 'r') as f:
    nsightful.display_ncu_csv_in_notebook(f)
```

If you want to profile cells with Nsightful without the Nsight JupyterLab extension, you can use
`%%writefile` to output a Python file that will be run under `ncu`. Note that with this approach,
the cell must be self contained; it cannot depend on any other cells.

```bash
!pip install "nsightful[notebook] @ git+https://github.com/brycelelbach/nsightful.git"
```

```python
%%writefile copy_blocked.py

from numba import cuda
import cupy as cp

total_items = 2**28
items_per_thread = 2**6
threads_per_block = 256
blocks = int(total_items / (threads_per_block * items_per_thread))

src = cp.arange(total_items)
dst = cp.empty_like(src)

@cuda.jit
def copy_blocked(src, dst, items_per_thread):
 base = cuda.grid(1) * items_per_thread
 for i in range(items_per_thread):
   dst[base + i] = src[base + i]

copy_blocked[blocks, threads_per_block](src, dst, items_per_thread)
```

```bash
!ncu -f --kernel-name regex:copy_blocked --set full -o copy_blocked python copy_blocked.py
```

```python
import nsightful

copy_blocked_csv = !ncu --import copy_blocked.ncu-rep --csv
nsightful.display_ncu_csv_in_notebook(copy_blocked_csv)
```

### Nsight Systems (NSYS)

#### Generating NSYS SQLite Data

First, you need to generate NSYS SQLite data from your CUDA application:

```bash
# Profile your application
nsys profile -o myreport ./myapplication

# Convert SQLite to Chrome Trace JSON (output to a file)
nsightful myreport.sqlite -o myreport.json
```

#### NSYS Python Conversion API

```python
import nsightful

# Convert SQLite file to Chrome Trace JSON string
with open('myreport.sqlite', 'rb') as f:
    json_content = nsightful.convert_nsys_sqlite_to_chrome_trace_json(f)
    print(json_content)

# Parse structured data for custom processing
with open('myreport.sqlite', 'rb') as f:
    nsys_data = nsightful.parse_nsys_sqlite(f)
    # nsys_data is a structured dictionary with trace events
```

#### NSYS Jupyter Notebook Widget

Nsightful provides a function to display NSYS data in [Perfetto](https://ui.perfetto.dev/), a visual profiler with a interactive timeline view.

If you have an existing report file or use the Nsight JupyterLab extension to run a cell under the profile and collect a report, then you can display it with Nsightful:

```python
!pip install "nsightful[notebook] @ git+https://github.com/brycelelbach/nsightful.git"
```

```python
import nsightful

nsightful.display_nsys_sqlite_file_in_notebook('myreport.sqlite')
```

or

```python
import nsightful

with open('myreport.sqlite', 'rb') as f:
    nsightful.display_nsys_sqlite_in_notebook(f)
```

If you want to profile cells with Nsightful without the Nsight JupyterLab extension, you can use `%%writefile` to output a Python file that will be run under `nsys`. Note that with this approach, the cell must be self contained; it cannot depend on any other cells.

```bash
!pip install "nsightful[notebook] @ git+https://github.com/brycelelbach/nsightful.git"
```

```python
%%writefile power_iteration.py

import cupy as cp

# Power iteration to find dominant eigenvector
size = 4096
iterations = 100

# Create a random symmetric matrix
A = cp.random.random((size, size), dtype=cp.float32)
A = (A + A.T) / 2  # Make symmetric

# Initial vector
b = cp.random.random(size, dtype=cp.float32)

for i in range(iterations):
    b_next = cp.dot(A, b)
    b = b_next / cp.linalg.norm(b_next)

cp.cuda.Device().synchronize()
```

```bash
!nsys profile -o power_iteration python power_iteration.py
```

```python
import nsightful

nsightful.display_nsys_sqlite_file_in_notebook('power_iteration.sqlite')
```

## Example Output

### NCU to Flat Markdown

```markdown
# mykernel

## Speed Of Light

| Metric Name | Metric Unit | Metric Value |
|-------------|-------------|--------------|
| DRAM Frequency | cycle/nsecond | 1.215 |
| SM Frequency | cycle/nsecond | 1.410 |

🔧 **OPTIMIZATION**: This kernel achieves 45% of the theoretical maximum DRAM bandwidth...

## Memory Workload

| Metric Name | Metric Unit | Metric Value |
|-------------|-------------|--------------|
| Memory Throughput | Gbyte/second | 256.7 |
| Memory Utilization | % | 18.2 |

⚠️ **WARNING**: Memory bandwidth utilization is low. Consider increasing arithmetic intensity...
```

## Nsight JupyterLab Extension

If you are using a Jupyter environment where you are able to install JupyterLab extensions, check
out [the Nsight JupyterLab extension](https://pypi.org/project/jupyterlab-nvidia-nsight/).
However, if you're using an environment like [Google Colab](https://colab.research.google.com/)
where you can't install extensions, or you prefer a simple graphical summary within notebook cells
instead of the full GUI experience, Nsightful might be for you.

The Nsight JupyterLab extension allows you to do two things:

- Profile a cell with Nsight Compute or Nsight Systems. We recommend using this with Nsightful's
  Jupyter widgets when possible.
- Run the Nsight GUIs within the notebook. This is a more full-featured alternative to Nsightful's
  Jupyter widgets.

## Requirements

- Python 3.8+
- For Jupyter notebook features: `ipywidgets>=7.0.0`, `IPython>=7.0.0`

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/brycelelbach/nsightful.git
cd nsightful

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/ --cov-report=html

# Run tests for specific Python versions (requires tox)
pip install tox
tox
```

### Running Code Quality Checks

The project uses several tools to maintain code quality:

```bash
# Format code with black
black src/ tests/

# Lint with flake8
flake8 --select=E9,F63,F7,F82 src/ tests/

# Type checking with mypy
mypy  --ignore-missing-imports src/
```

## License

This project is licensed under the BSD-3-Clause License. See [LICENSE](LICENSE) for details.
