import logging

import typer
from rich.logging import RichHandler

from .ffmpeg import ffmpeg
from .proj import projects

# from .yt import yt

app = typer.Typer()

FORMAT = "%(message)s"
logging.basicConfig(
    level="DEBUG", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


app.add_typer(projects, name="proj", help="Create and manage projects.")
app.add_typer(ffmpeg, name="ffmpeg", help="Work with FFmpeg.")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
