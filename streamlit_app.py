"""RecallKit Streamlit app.

This module provides a Streamlit UI for converting uploaded Markdown notes
into flashcards, saving them as JSON/TSV, and reviewing them in a study view.

Key features:
  * Upload .md files and convert them to flashcards (JSON + Quizlet TSV).
  * List, download, and delete existing flashcard sets.
  * Study interface rendered via an HTML template.

Environment variables:
  RECALLKIT_API_TOKEN: Token injected into the study UI.
  RECALLKIT_DATA_DIR:  (optional) Path for data storage; defaults to '/app/data/progress'.
  RECALLKIT_API_BASE:  (optional) Base URL for the study UI API; defaults to 'http://localhost:8502/api'.
"""

from __future__ import annotations

import os
import glob
import json
import base64
from pathlib import Path
from typing import Iterable, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

from src.utils import build_outputs, write_topics_index


# --- Configuration constants 

API_TOKEN: str = os.getenv("RECALLKIT_API_TOKEN", "")
DATA_DIR: str = os.getenv("RECALLKIT_DATA_DIR", "/app/data/progress")
BUILD_DIR: str = "static/web/build"
FAVICON_PATH: str = "static/favicon.png"
STUDY_TEMPLATE_PATH: str = "static/study.html"


# --- Streamlit page config 

st.set_page_config(page_title="RecallKit", layout="wide")


def load_favicon(path: str = FAVICON_PATH) -> None:
    """Load and inject a favicon into the app if it exists.

    Args:
        path (str): Path to the favicon image file (PNG).
    """
    p = Path(path)
    if not p.exists():
        return

    with p.open("rb") as f:
        favicon_b64 = base64.b64encode(f.read()).decode("utf-8")

    favicon_html = f'<link rel="icon" href="data:image/png;base64,{favicon_b64}">'
    st.markdown(favicon_html, unsafe_allow_html=True)


def gather_uploaded_markdown(uploaded_files: Iterable[st.runtime.uploaded_file_manager.UploadedFile]
                             ) -> List[Tuple[str, str]]:
    """Read uploaded Markdown files into (filename, text) tuples.

    Args:
        uploaded_files: Streamlit UploadedFile iterable.

    Returns:
        list[tuple[str, str]]: (original filename, decoded UTF-8 text) pairs.
    """
    md_files: List[Tuple[str, str]] = []
    for f in uploaded_files or []:
        text = f.read().decode("utf-8")
        md_files.append((f.name, text))
    return md_files


def save_flashcard_assets(topic: str, cards_json: str, quizlet_tsv: str, build_dir: str = BUILD_DIR) -> int:
    """Persist JSON and TSV flashcard assets to disk.

    Creates the build directory if needed, writes the JSON and TSV files,
    and refreshes the topic index via `write_topics_index`.

    Args:
        topic (str): Topic name (filename stem, no extension).
        cards_json (str): Serialised JSON content for the flashcards.
        quizlet_tsv (str): Tab-separated Q/A pairs for Quizlet import.
        build_dir (str): Directory in which to save outputs.

    Returns:
        int: The number of flashcards saved (parsed from the JSON payload).
    """
    Path(build_dir).mkdir(parents=True, exist_ok=True)

    json_path = Path(build_dir) / f"{topic}.json"
    tsv_path = Path(build_dir) / f"{topic}.tsv"

    # Write files
    json_path.write_text(cards_json, encoding="utf-8")
    tsv_path.write_text(quizlet_tsv, encoding="utf-8")

    # Count cards for message (parse lightly to avoid recomputation upstream)
    try:
        count = len(json.loads(cards_json).get("cards", []))
    except Exception:
        count = 0

    # Update topics index
    write_topics_index()

    return count


def list_flashcard_json_files(build_dir: str = BUILD_DIR) -> List[Path]:
    """List JSON flashcard set files in the build directory.

    Args:
        build_dir (str): Directory to scan.

    Returns:
        list[pathlib.Path]: Paths to '*.json' files.
    """
    return [Path(p) for p in glob.glob(os.path.join(build_dir, "*.json"))]


def render_manage_tab() -> None:
    """Render the 'Manage Flashcards' tab.

    Provides:
      * Upload form for Markdown notes and conversion to flashcards.
      * List of existing sets with download buttons (JSON/TSV) and delete actions.
    """
    st.header("Upload Markdown Notes")
    topic = st.text_input("Topic name (used for file naming)", "default")
    uploaded_files = st.file_uploader("Drop your .md files here", type=["md"], accept_multiple_files=True)

    if uploaded_files and st.button("Convert to Flashcards"):
        md_files = gather_uploaded_markdown(uploaded_files)
        cards_json, quizlet_tsv, cards = build_outputs(md_files)
        count = save_flashcard_assets(topic=topic, cards_json=cards_json, quizlet_tsv=quizlet_tsv, build_dir=BUILD_DIR)
        st.success(f"✅ Saved {count} flashcards to {topic}.json")

    st.subheader("Existing Flashcard Sets")
    json_files = list_flashcard_json_files()

    st.subheader("Download")
    if json_files:
        for jf in json_files:
            fname = jf.name
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(fname)
            with col2:
                with jf.open("rb") as f:
                    st.download_button("⬇️ JSON", f, file_name=fname, key=f"dl_json_{fname}")
            with col3:
                tsv_path = jf.with_suffix(".tsv")
                if tsv_path.exists():
                    with tsv_path.open("rb") as f:
                        st.download_button("⬇️ TSV", f, file_name=tsv_path.name, key=f"dl_tsv_{fname}")

    st.subheader("Delete")
    if json_files:
        for jf in json_files:
            fname = jf.name
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(fname)
            with col2:
                if st.button("🗑️ Delete", key=f"del_{fname}"):
                    jf.unlink(missing_ok=True)
                    tsv = jf.with_suffix(".tsv")
                    if tsv.exists():
                        tsv.unlink(missing_ok=True)
                    write_topics_index()
                    st.warning(f"Deleted {fname}")
                    st.rerun()
    else:
        st.info("No flashcard sets yet.")


def render_study_tab() -> None:
    """Render the ‘FlashCards’ study tab.

    Aggregates all card JSON files (excluding shared indexes), injects them
    into the study HTML template, and renders it within the Streamlit app.
    """
    json_files = [
        p for p in list_flashcard_json_files()
        if p.name not in ("cards.json", "topics.json")
    ]

    if not json_files:
        st.info("No flashcard sets found. Please upload notes first in ‘Manage Flashcards’.")
        return

    # Collate all cards with topic labels
    all_cards = []
    for path in json_files:
        topic_name = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        cards = data.get("cards", [])
        for c in cards:
            c["topic"] = topic_name
        all_cards.extend(cards)

    # Load HTML template
    template_path = Path(STUDY_TEMPLATE_PATH)
    if not template_path.exists():
        st.error(f"Template not found: {template_path}")
        return

    template = template_path.read_text(encoding="utf-8")
    cards_json = json.dumps(all_cards, ensure_ascii=False)

    # Avoid shadowing stdlib names; use a descriptive variable
    rendered_html = (
        template
        .replace("__CARDS__", cards_json)
        .replace("__API_TOKEN__", API_TOKEN)
        .replace("__API_BASE__", os.getenv("RECALLKIT_API_BASE", "http://localhost:8502/api"))
    )

    components.html(rendered_html, height=1000, scrolling=True)


def main() -> None:
    """Entry point for the Streamlit UI."""
    load_favicon()

    tab1, tab2 = st.tabs(["🎓 FlashCards", "📂 Manage Flashcards"])

    with tab2:
        render_manage_tab()

    with tab1:
        render_study_tab()


# Run the app 
main()
