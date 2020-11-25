# datasette-ripgrep

[![PyPI](https://img.shields.io/pypi/v/datasette-ripgrep.svg)](https://pypi.org/project/datasette-ripgrep/)
[![Changelog](https://img.shields.io/github/v/release/simonw/datasette-ripgrep?include_prereleases&label=changelog)](https://github.com/simonw/datasette-ripgrep/releases)
[![Tests](https://github.com/simonw/datasette-ripgrep/workflows/Test/badge.svg)](https://github.com/simonw/datasette-ripgrep/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/datasette-ripgrep/blob/main/LICENSE)

HIGHLY EXPERIMENTAL: Configurable Datasette plugin running ripgrep

This plugin is a weird experiment. It probably shouldn't even be a Datasette plugin at all! Do not attempt to run this on a public Datasette instance.

## Installation

Install this plugin in the same environment as Datasette.

    $ datasette install datasette-ripgrep

The `rg` executable needs to be installed such that it can be run by this tool.

## Usage

This plugin requires configuration: it needs to a `path` setting so that it knows where to run searches:

```json
{
    "plugins": {
        "datasette-ripgrep": {
            "path": "/path/to/your/files"
        }
    }
}
```

The plugin will add an interface at `/-/ripgrep` for running searches.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-ripgrep
    python3 -mvenv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and tests:

    pip install -e '.[test]'

To run the tests:

    pytest
