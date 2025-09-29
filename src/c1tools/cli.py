import logging

import typer
from rich.logging import RichHandler

from .proj import projects

app = typer.Typer()

FORMAT = "%(message)s"
logging.basicConfig(
    level="DEBUG", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


app.add_typer(projects, name="proj", help="Create and manage projects.")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
