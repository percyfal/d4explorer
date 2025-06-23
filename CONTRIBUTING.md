# Contributor guide

Thank you for your interest in improving this project. This project is
open-source under the [MIT license] and welcomes contributions in the
form of bug reports, feature requests, and pull requests.

Here is a list of important resources for contributors:

- [Source Code]
- [Issue Tracker]

[mit license]: https://opensource.org/licenses/MIT
[source code]: https://github.com/percyfal/d4explorer
[issue tracker]: https://github.com/percyfal/d4explorer/issues

## Development environment

Project and package management is done using [pixi].

Use pixi to add and remove dependencies from `pyproject.toml`.
Development packages are added by applying the `--feature dev` flag:

    pixi add package
    pixi add --feature dev dev-package
    pixi remove package
    pixi remove --feature dev dev-package

To activate a shell, run `pixi shell`.

[pixi]: https://pixi.sh/dev/

## Virtual environment

`pixi` sets up virtual environments in `.pixi`. To activate an
environment run `pixi shell -e environment`. You can also run programs
in the virtual environment with `pixi run -e environment`, e.g.,

    pixi run -e dev pytest -v -s

## Linting and testing workflow

`pixi` provides support for Python code formatting, linting, and more.
You can run the entire linting toolchain with

    pixi run lint

## Development with small test data set

FIXME

## Serving the application in development mode

For interactive development, you can serve the app in development mode
with `panel serve`:

    pixi run panel serve src/d4explorer --dev --show --args serve

## Monitoring resource usage and user behaviour

The `--admin` option will activate the `/admin` panel:

    pixi run panel serve src/d4explorer --dev --show --admin --args serve

If the project is served locally on port 5006, the `/admin` endpoint
would be available at <http://localhost:5006/admin>. See [admin] for
more information.

[admin]: https://panel.holoviz.org/how_to/profiling/admin.html
