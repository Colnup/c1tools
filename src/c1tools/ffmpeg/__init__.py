"""ffmpeg cli module for c1tools.

This module aims to help using the often complex ffmepg command line tool.
The aim is NOT to provide 100% of ffmpeg features, but to cover the most common use cases
through simple commands."""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import typer

log = logging.getLogger(__name__)

ffmpeg = typer.Typer()


# --------------------------------------------------------------------------------
# utils
# --------------------------------------------------------------------------------
CACHE_FILE = Path(__file__).parent / "encoder_cache.json"


def test_encoder(encoder: str) -> bool:
    """
    Test if a given encoder actually works by running a short encode to null.
    Returns True if usable, False otherwise.
    """
    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=128x128:rate=1:duration=1",
            "-c:v",
            encoder,
            "-t",
            "1",
            "-f",
            "null",
            "-",
        ]
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def build_encoder_cache(force_refresh: bool = False) -> dict[str, bool]:
    """
    Build and persist a cache of usable encoders.
    If cache exists and force_refresh is False, load it.
    """
    if CACHE_FILE.exists() and not force_refresh:
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                log.info(f"Loaded encoder cache from {CACHE_FILE}")
                return cache
        except Exception:
            log.warning("Failed to load encoder cache, rebuilding...")

    # Cache not found or force refresh
    candidates = [
        "av1_nvenc",
        "av1_qsv",
        "av1_amf",
        "libaom-av1",
        "hevc_nvenc",
        "hevc_qsv",
        "hevc_amf",
        "libx265",
        "h264_nvenc",
        "h264_qsv",
        "h264_amf",
        "libx264",
    ]

    cache = {enc: test_encoder(enc) for enc in candidates}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
    log.info(f"Encoder cache built and saved to {CACHE_FILE}")
    return cache


def select_encoder(
    authorized_encoders: tuple[str, ...] = ("av1", "hevc", "h264"),
    force_refresh: bool = False,
) -> str:
    """
    Select the best working encoder from authorized list.
    Uses persistent cache.
    """
    cache = build_encoder_cache(force_refresh)

    candidates = []
    if "av1" in authorized_encoders:
        candidates += ["av1_nvenc", "av1_qsv", "av1_amf", "libaom-av1"]
    if "hevc" in authorized_encoders:
        candidates += ["hevc_nvenc", "hevc_qsv", "hevc_amf", "libx265"]
    if "h264" in authorized_encoders:
        candidates += ["h264_nvenc", "h264_qsv", "h264_amf", "libx264"]

    for enc in candidates:
        if cache.get(enc, False):
            log.info(f"Using encoder: {enc}")
            return enc

    log.warning("No working encoder found, falling back to libx264")
    return "libx264"


def get_duration(input_file: str) -> float:
    """
    Return video duration in seconds.
    """
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_file,
        ],
        capture_output=True,
        text=True,
    )
    return float(probe.stdout.strip())


# --- Load tiers from JSON config ---
def load_tiers_config_json() -> List[Dict[str, Any]]:
    config_path = Path(__file__).parent / "tiers_config.json"
    with open(config_path, "r") as f:
        return json.load(f)


def compress_video(
    input_file: str,
    output_file: str,
    target_size_mb: int | float,
    audio_bitrate: str = "128k",
    authorized_encoders: tuple[str, ...] = ("av1", "hevc", "h264"),
    force_cache_refresh: bool = False,
) -> None:
    """
    Compress video to a target size using the best available encoder.
    """
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg/ffprobe not found in PATH")

    encoder = select_encoder(authorized_encoders, force_refresh=force_cache_refresh)
    duration = get_duration(input_file)

    target_size_bits = target_size_mb * 1024 * 1024 * 8
    audio_bitrate_kbps = int(audio_bitrate.replace("k", ""))
    audio_size_bits = audio_bitrate_kbps * 1000 * duration
    video_size_bits = target_size_bits - audio_size_bits
    video_bitrate = int(video_size_bits / duration / 1000)

    log.info(f"Duration: {duration:.2f}s")
    log.info(f"Target video bitrate: {video_bitrate}k")

    tiers = load_tiers_config_json()

    # --- Select best tier ---
    def select_tier(tiers: List[Dict[str, Any]], video_bitrate: int) -> Dict[str, Any]:
        for tier in tiers:
            if video_bitrate >= tier["min_bitrate_kbps"]:
                return tier
        return tiers[-1]  # fallback to lowest

    selected_tier = select_tier(tiers, video_bitrate)
    log.info(
        f"Selected tier: {selected_tier['resolution']}p{selected_tier['framerate']}"
    )

    # --- Build ffmpeg filters ---
    vf_filter = []
    if selected_tier["resolution"]:
        vf_filter += ["-vf", f"scale=-2:{selected_tier['resolution']}"]
    # Framerate filter
    if selected_tier["framerate"]:
        vf_filter += ["-r", str(selected_tier["framerate"])]

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        *vf_filter,
        "-c:v",
        encoder,
        "-b:v",
        f"{video_bitrate}k",
        "-maxrate",
        f"{video_bitrate}k",
        "-bufsize",
        f"{2 * video_bitrate}k",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        output_file,
    ]

    log.debug(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    log.info("Compression complete")


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
def discord(
    input_file: str,
    output_file: str,
    encoder: str = "h264",
    target_size_mb: float = 10,
) -> None:
    """Convert a video file to a Discord-compatible format using ffmpeg."""
    target_size_mb -= 0.2
    compress_video(
        input_file,
        output_file,
        target_size_mb=target_size_mb,
        audio_bitrate="128k",
        authorized_encoders=(encoder,),
    )
