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

Project and package management is done using [rye]. For a good
introduction to rye, see the [postmodern python] blog post.

Use rye to add and remove dependencies from `pyproject.toml`.
Development packages are added by applying the `--dev` flag:

    rye add package
    rye add dev-package --dev
    rye remove package
    rye remove dev-package --dev

After modifying dependencies, make sure to run `rye sync` to update
the virtual environment.

[rye]: https://rye.astral.sh/
[postmodern python]: https://rdrn.me/postmodern-python/

## Virtual environment

rye sets up a virtual environment in `.venv`. You should be able to
activate the environment with `source .venv/bin/activate`. However, if
you have `pyenv` installed you may run into the issue that nothing
seems to load. This is a known issue (see [pyenv issue]). You can
always run programs in the virtual environment with `rye run`, e.g.,

    rye run pytest -v -s

[pyenv issue]: https://github.com/astral-sh/rye/issues/317

## Linting and testing workflow

rye provides support for Python code formatting, linting, and more.
The steps can be run separately

    rye fmt
    rye lint --fix
    rye run check
    rye test

Alternatively, you can run the entire toolchain with

    rye run all

## Development with small test data set

FIXME

## Monitoring resource usage and user behaviour

The `--admin` option will activate the `/admin` panel:

    rye run python -m d4explorer tests/data/test.trees --admin

If the project is served locally on port 5006, the `/admin` endpoint
would be available at `http://localhost:5006/admin. See [admin] for
more information.

[admin]: https://panel.holoviz.org/how_to/profiling/admin.html

## Serving the application in development mode

For interactive development, you can serve the app in development mode
with `panel serve`:

    rye run panel serve src/d4explorer --dev --show --args D4FILE
