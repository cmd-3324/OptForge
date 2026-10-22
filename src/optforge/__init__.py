"""OptForge package entry points."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("optforge")
except PackageNotFoundError:
    __version__ = "0.1.0"


def main() -> None:
    """Simple top-level entry point for the package."""
    import typer

    app = typer.Typer(
        help="OptForge developer utilities",
        no_args_is_help=True,
        add_completion=False,
    )

    @app.command("list")
    def list_commands() -> None:
        typer.echo("Available commands:")
        typer.echo("  diskcheck")
        typer.echo("  envcheck")
        typer.echo("  portcheck")
        typer.echo("  pycacheClean")

    app()
