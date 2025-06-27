# netquery

## Purpose
`netquery` is a Python CLI tool designed to connect to network devices over SSH and run commands. It supports device autodetection, command execution, and output parsing using TextFSM.

## Installation (Development Mode)

### 1. Clone the repository & move inside
```sh
git clone https://github.com/Diegomcha/netquery.git
cd netquery
```

### 2. Create a virtual environment (optional but recommended)
```sh
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
```

### 3. Install package in editable mode with dev utilities
```sh
pip install -e .[dev]
```

## Building
To build the source and wheel distributions:
```sh
python -m build
```
This will generate .tar.gz and .whl files in the dist/ directory.

## Usage
After installation, you can run the CLI using:
```sh
netquery
```