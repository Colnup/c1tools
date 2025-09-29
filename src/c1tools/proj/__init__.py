"""Proj CLI component.

Helper pour créer des documents propres depuis des sources markdown"""

import datetime
import logging
import os
import shutil
import subprocess
from pathlib import Path
from time import time

import typer

log = logging.getLogger(__name__)

projects = typer.Typer()
create = typer.Typer()
lang = typer.Typer()
projects.add_typer(create, name="create", help="Create a new project.")
projects.add_typer(lang, name="lang", help="Manage project languages.")


# --------------------------------------------------------------------------------
# Global variables
# --------------------------------------------------------------------------------

TD_LATEX_HEADER = Path(__file__).parent / "latex" / "td_header.tex"
WORKDIR = Path.cwd()

# --------------------------------------------------------------------------------
# Utils
# --------------------------------------------------------------------------------


def download_dir() -> Path:
    if Path.home().joinpath("Téléchargements").exists():
        return Path.home() / "Téléchargements"
    return Path.home() / "Downloads"


def get_latest_downloads(max_age_in_minutes: int = 5) -> list[Path]:
    all_files = list(download_dir().glob("*"))
    filtered_files = [
        f for f in all_files if f.stat().st_mtime >= (time() - max_age_in_minutes * 60)
    ]
    return sorted(filtered_files, key=lambda x: x.stat().st_mtime, reverse=True)


# --------------------------------------------------------------------------------
# c1 project
# --------------------------------------------------------------------------------


@projects.command()
def rendu(overwrite: bool = True) -> None:
    """Convert all markdown files in the current directory to PDF using Pandoc."""

    md_files = list(WORKDIR.glob("*_rendu_Colin_PROKOPOWICZ.md"))
    if not md_files:
        log.warning("No markdown files found in the current directory.")
        return

    for md_file in md_files:
        pdf_file = md_file.with_suffix(".pdf")
        if pdf_file.exists():
            if overwrite:
                log.info(f"Overwriting existing PDF file {pdf_file.name}.")
                pdf_file.unlink()
            else:
                log.info(f"PDF file {pdf_file.name} already exists. Skipping.")
                continue

        log.info(f"Converting {md_file.name} to PDF...")
        try:
            # pandoc -s -o rendu.pdf --number-sections --include-in-header=header.tex *.md
            subprocess.run(
                [
                    "pandoc",
                    "-s",
                    "-o",
                    str(pdf_file),
                    "--number-sections",
                    f"--include-in-header={TD_LATEX_HEADER}",
                    str(md_file),
                ],
                check=True,
            )
            log.info(f"Converted {md_file.name} to {pdf_file.name} successfully.")
        except subprocess.CalledProcessError as e:
            log.exception(f"Error converting {md_file.name} to PDF: {e}")


# --------------------------------------------------------------------------------
# c1 project create
# --------------------------------------------------------------------------------


@create.command()
def generic_project(
    project_type: str,
    download_max_age: int = 5,
    move_instead_of_copy: bool = True,
) -> None:
    """Create a new project of the specified type in the current working directory."""

    # Auto determine TD number from the already existing TD directories
    existing_project_type_dirs = [
        d for d in WORKDIR.iterdir() if d.is_dir() and d.name.startswith(project_type)
    ]
    if existing_project_type_dirs:
        existing_project_type_numbers = [
            int(d.name[2:]) for d in existing_project_type_dirs if d.name[2:].isdigit()
        ]
        next_project_type_number = max(existing_project_type_numbers) + 1
    else:
        next_project_type_number = 1
    project_dir_name = f"{project_type}{next_project_type_number:02d}"
    project_dir_path = WORKDIR / project_dir_name

    project_dir_path.mkdir(exist_ok=True)

    log.info(f"Creating a new {project_type} project in {project_dir_path}...")

    # Copy latest downloaded files to the new project directory
    latest_downloads = get_latest_downloads(download_max_age)
    if not latest_downloads:
        log.warning("No recent downloads found to copy.")
    else:
        for file_path in latest_downloads:
            destination = project_dir_path / file_path.name
            if destination.exists():
                log.info(
                    f"File {file_path.name} already exists in {project_dir_path}. Skipping."
                )
            else:
                if move_instead_of_copy:
                    log.info(f"Moving {file_path.name}...")
                    shutil.move(file_path, destination)
                else:
                    log.info(f"Copying {file_path.name}...")
                    if file_path.is_file():
                        shutil.copy2(file_path, destination)
                    elif file_path.is_dir():
                        shutil.copytree(file_path, destination)

    # Create a {filename}_rendu_Colin_PROKOPOWICZ.md file for each pdf file
    _create_md_files_for_pdfs(next_project_type_number, project_dir_path)
    os.chdir(project_dir_path)
    log.info(f"Project {project_dir_name} created successfully.")


def _create_md_files_for_pdfs(
    fallback_project_type_number: int, destination: Path
) -> None:
    """Create a {filename}_rendu_Colin_PROKOPOWICZ.md file for each pdf file in the destination directory."""

    markdown_header = f"""---
title: "Rendu {{title}}"
author: "Colin PROKOPOWICZ"
date: "{datetime.date.today().isoformat()}"
---

# {{title}}

"""

    pdf_files = list(destination.glob("*.pdf"))
    if not pdf_files:
        log.warning(
            "No PDF files found in the new project directory. Creating single rendu file."
        )
        title = f"project{fallback_project_type_number:02d}_rendu_Colin_PROKOPOWICZ"
        md_filename = title + ".md"
        md_filepath = destination / md_filename
        md_content = markdown_header.format(title=title)
        md_filepath.write_text(md_content, encoding="utf-8")
        log.info(f"Markdown file {md_filename} created successfully.")
    else:
        for pdf_file in pdf_files:
            md_filename = pdf_file.stem + "_rendu_Colin_PROKOPOWICZ.md"
            md_filepath = destination / md_filename
            if md_filepath.exists():
                log.info(f"Markdown file {md_filename} already exists. Skipping.")
            else:
                log.info(f"Creating markdown file {md_filename}...")
                md_content = markdown_header.format(title=pdf_file.stem)
                md_filepath.write_text(md_content, encoding="utf-8")
                log.info(f"Markdown file {md_filename} created successfully.")


@create.command()
def td(download_max_age: int = 5) -> None:
    generic_project("td", download_max_age)


@create.command()
def tp(download_max_age: int = 5) -> None:
    generic_project("tp", download_max_age)


# --------------------------------------------------------------------------------
# c1 project language
# --------------------------------------------------------------------------------


@lang.command()
def add(lang_code: str) -> None:
    """Add a new language to the project."""
    log.debug(f"Adding language {lang_code} to the project...")
    match lang_code:
        case "python" | "py":
            _add_lang_python()
        case _:
            log.error(f"Language {lang_code} is not supported.")
            return
    log.info(f"Language {lang_code} added successfully.")


def _add_lang_python() -> None:
    """Setup current workdir for python development."""
    log.info("Setting up Python development environment...")
    subprocess.run(
        [
            "uv",
            "init",
            "--python",
            "3",
            "--pre-commit",
        ]
    )
