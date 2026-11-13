"""The ``optforge`` dispatcher that exposes every tool as a subcommand."""

from __future__ import annotations

from typing import Annotated

import typer

from optforge.core.version import get_version
from optforge.diskcheck.cli import app as diskcheck_app
from optforge.envcheck.cli import app as envcheck_app
from optforge.portcheck.cli import app as portcheck_app
from optforge.pycacheclean.cli import app as pycacheclean_app
from optforge.volume.cli import app as volume_app

app = typer.Typer(
    name="optforge",
    help="Developer utilities for ports, environment variables, disk usage, Python caches, and volume.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"optforge {get_version()}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    pass


app.add_typer(portcheck_app, name="portcheck")
app.add_typer(envcheck_app, name="envcheck")
app.add_typer(diskcheck_app, name="diskcheck")
app.add_typer(pycacheclean_app, name="pycache-clean")
app.add_typer(pycacheclean_app, name="pycacheClean", hidden=True)
app.add_typer(volume_app, name="vol")


if __name__ == "__main__":
    app()
