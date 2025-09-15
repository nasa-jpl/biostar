# OpenBioSTAR

Open source release of the NASA BioSTAR (Bioburden Sampling Tool for Assessing Risk) codebase, developed by the Jet Propulsion Laboratory.

## Local Development Setup

First make sure Python 3.12 and [Poetry](https://python-poetry.org/) are installed, then create + activate a Python 3.12 virtual environment, for example:

```bash
python3 -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows
.venv/Scripts/activate
```

Now install the project dependencies using Poetry:

```bash
poetry install
```

Create a file `.env` (at the project root) defining the required environment variables (see `example.env`).

Now run the server locally:

```bash
make runserver  # shortcut for 'python3 -m biostar.app'
```

## Analogy Configuration

BioSTAR can be configured to use your own set of project-specific analogies instead of the generic defaults defined in `biostar/data` by setting defining the optional environment variables in documented in `example.env`. See below for details on each:

- `PATH_HIERARCHY`: path to an XLSX file that defines the hierarchical structure of analogy hardware elements; see [the default file](./biostar/data/hierarchy_default.xlsx) for formatting details
- `PATH_POSTERIOR`: path to a JSON file mapping each analogy hardware element to a posterior array of bioburden values (keys should be names of hardware elements as they appear in the hierarchy XLSX file)
    - This is typically generated using [this script](./scripts/process_posterior_excel.py) to process the XLSX output from the [underlying Bayesian model](https://github.com/idaholab/HELP)
- `PATH_SEMANTIC_MAP`: path to a JSON file mapping each analogy hardware element to a new name for display in the tool (keys should be names of the hardware elements as they appear in the hierarchy XLSX file and values should be the new name)
- `PATH_METADATA`: path to a JSON file mapping each analogy hardware element to a set of metadata for display in the tool (keys should be the RENAMED hardware elements, if applicable); see [the default file](./biostar/data/metadata_default.json) for the metadata fields that should be defined for each analogy
