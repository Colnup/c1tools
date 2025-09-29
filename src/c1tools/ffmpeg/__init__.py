"""ffmpeg cli module for c1tools.

This module aims to help using the often complex ffmepg command line tool.
The aim is NOT to provide 100% of ffmpeg features, but to cover the most common use cases
through simple commands."""

import logging
import subprocess

import typer

log = logging.getLogger(__name__)

ffmpeg = typer.Typer()

# --------------------------------------------------------------------------------
# c1 ffmpeg
# --------------------------------------------------------------------------------


@ffmpeg.command()
def to_mp4(input_file: str, output_file: str) -> None:
    """Convert a video file to MP4 format using ffmpeg."""

    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_file,
    ]
    log.debug(f"Running command: {' '.join(command)}")
    subprocess.run(command, check=True)
    log.info(f"Converted {input_file} to {output_file} successfully.")


@ffmpeg.command()
def discord(input_file: str, output_file: str) -> None:
    """Convert a video file to a Discord-compatible format using ffmpeg."""

    MAX_RESOLUTION = (1280, 720)
    MAX_FILE_SIZE_MB = 10

    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-vf",
        f"scale='min({MAX_RESOLUTION[0]},iw)':'min({MAX_RESOLUTION[1]},ih)':force_original_aspect_ratio=decrease",
        "-c:v",
        "libx264",
        "-b:v",
        "2500k",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-fs",
        f"{MAX_FILE_SIZE_MB}M",
        output_file,
    ]
    log.debug(f"Running command: {' '.join(command)}")
    subprocess.run(command, check=True)
    log.info(
        f"Converted {input_file} to Discord-compatible {output_file} successfully."
    )
