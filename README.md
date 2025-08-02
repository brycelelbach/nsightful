# ncu2markdown

[![Apache 2.0 with LLVM exceptions](https://img.shields.io/badge/license-Apache%202.0%20with%20LLVM%20exceptions-blue.svg)](LICENSE)

Convert [NVIDIA Nsight Compute](https://developer.nvidia.com/nsight-compute) CSV output to Markdown
that can be output to a file or displayed in a tabbed widget in Jupyter notebooks.

## Installation

If you just need the command line tool:

```bash
pip install git+https://github.com/brycelelbach/ncu2markdown.git
```

If you want to use the Jupyter notebook widget:

```bash
pip install "git+https://github.com/brycelelbach/ncu2markdown.git[notebook]"
```

## Quick Start

### Generating NCU CSV Data

First, you need to generate NCU CSV data from your CUDA application:

```bash
# Profile your application
ncu --set full -o myreport ./myapplication

# Export to CSV
ncu --import myreport.ncu-rep --csv > myreport.csv

# Convert CSV to Markdown (output to a file)
ncu2markdown myreport.csv -o myreport.md
```

### Python API Usage

```python
import ncu2markdown

# Convert CSV file to Markdown string
with open('myreport.csv', 'r') as f:
    markdown_content = ncu2markdown.convert_ncu_csv_to_flat_markdown(f)
    print(markdown_content)

# Parse structured data for custom processing
with open('myreport.csv', 'r') as f:
    ncu_data = ncu2markdown.parse_ncu_csv_data(f)
    # ncu_data is a nested dictionary with kernel -> section -> metrics/rules
```

### Jupyter Notebook Usage

If you are using a Jupyter environment where you are able to install JupyterLab extensions, check
out [the Nsight Compute JupyterLab extension](https://pypi.org/project/jupyterlab-nvidia-nsight/),
which allows you to profile a cell with Nsight Compute or Nsight Systems and can run the Nsight
GUIs within the notebook.

However, if you're using an environment like Google Colab where you can't install extensions, or
you prefer a simple graphical summary instead of the full GUI experience, ncu2markdown might be for
you. It provides a function to display NCU data in a Jupyter notebook widget, reminiscent of the
Nsight Compute GUI. This widget has:
- A kernel selector dropdown.
- A summary tab showing all Nsight recommendations and advisories.
- One detailed tab for each Nsight compute section.

If you have an existing report file or use the Nsight JupyterLab extension to run a cell under the
profile and collect a report, then you can display it with ncu2markdown:

```python
!pip install "git+https://github.com/brycelelbach/ncu2markdown.git[notebook]"
```

```python
import ncu2markdown

with open('myreport.csv', 'r') as f:
    ncu2markdown.display_ncu_data_in_notebook(f)
```

If you want to profile cells with ncu2markdown without the Nsight JupyterLab extension, you can use
`%%writefile` to output a Python file that will be run under `ncu`. Note that with this approach,
the cell must be self contained; it cannot depend on any other cells.

```bash
!pip install "git+https://github.com/brycelelbach/ncu2markdown.git[notebook]"
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
import ncu2markdown

copy_blocked_csv = !ncu --import copy_blocked.ncu-rep --csv
ncu2markdown.display_ncu_data_in_notebook(copy_blocked_csv)
```

## Example Output

### Command Line

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

## Requirements

- Python 3.8+
- For Jupyter notebook features: `ipywidgets>=7.0.0`, `IPython>=7.0.0`

## License

This project is licensed under the Apache License 2.0 with LLVM exceptions - see the [LICENSE](LICENSE) file for details.
