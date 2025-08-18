import os, glob, json
import streamlit as st
import streamlit.components.v1 as components
import parser
import json
import html


# Load environment config
API_TOKEN = os.getenv("RECALLKIT_API_TOKEN", "")
DATA_DIR = os.getenv("RECALLKIT_DATA_DIR", "/app/data/progress")

BUILD_DIR = "static/web/build" 

st.set_page_config(page_title="RecallKit", layout="wide")

import base64

# Load favicon as base64
favicon_path = "static/favicon.png"
if os.path.exists(favicon_path):
    with open(favicon_path, "rb") as f:
        favicon_data = f.read()
    favicon_b64 = base64.b64encode(favicon_data).decode()
    favicon_html = f"""
        <link rel="icon" href="data:image/png;base64,{favicon_b64}">
    """
    st.markdown(favicon_html, unsafe_allow_html=True)


tab1, tab2, tab3 = st.tabs(["📂 Manage Flashcards", "🎓 Study", "ℹ️ Help"])


def write_topics_index():
    os.makedirs(BUILD_DIR, exist_ok=True)
    topics = []
    for path in glob.glob(os.path.join(BUILD_DIR, "*.json")):
        base = os.path.basename(path)
        if base in ("cards.json", "topics.json"):
            continue
        topics.append(os.path.splitext(base)[0])
    with open(os.path.join(BUILD_DIR, "topics.json"), "w", encoding="utf-8") as f:
        json.dump({"topics": sorted(topics)}, f, ensure_ascii=False, indent=2)

with tab1:
    st.header("Upload Markdown Notes")
    topic = st.text_input("Topic name (used for file naming)", "default")
    uploaded_files = st.file_uploader("Drop your .md files here", type=["md"], accept_multiple_files=True)

    if uploaded_files and st.button("Convert to Flashcards"):
        md_files = [(f.name, f.read().decode("utf-8")) for f in uploaded_files]
        cards_json, quizlet_tsv, cards = parser.build_outputs(md_files)

        os.makedirs(BUILD_DIR, exist_ok=True)
        json_path = os.path.join(BUILD_DIR, f"{topic}.json")
        tsv_path  = os.path.join(BUILD_DIR, f"{topic}.tsv")

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(cards_json)
        with open(tsv_path, "w", encoding="utf-8") as f:
            f.write(quizlet_tsv)

        write_topics_index()
        st.success(f"✅ Saved {len(cards)} flashcards to {topic}.json")

    st.subheader("Existing Flashcard Sets")
    json_files = glob.glob(os.path.join(BUILD_DIR, "*.json"))
    st.subheader("Download")
    if json_files:
        for jf in json_files:
            fname = os.path.basename(jf)
            topic_name = os.path.splitext(fname)[0]

            col1, col2, col3 = st.columns([3,1,1])
            with col1:
                st.write(fname)
            with col2:
                # Download JSON
                with open(jf, "rb") as f:
                    st.download_button("⬇️ JSON", f, file_name=fname, key=f"dl_json_{fname}")
            with col3:
                # Download TSV if exists
                tsv_path = jf.replace(".json", ".tsv")
                if os.path.exists(tsv_path):
                    with open(tsv_path, "rb") as f:
                        st.download_button("⬇️ TSV", f, file_name=os.path.basename(tsv_path), key=f"dl_tsv_{fname}")
    st.subheader("Delete")
    if json_files:
        for jf in json_files:
            fname = os.path.basename(jf)
            col1, col2 = st.columns([3,1])
            with col1: st.write(fname)
            with col2:
                if st.button("🗑️ Delete", key=f"del_{fname}"):
                    os.remove(jf)
                    tsv = jf.replace(".json", ".tsv")
                    if os.path.exists(tsv): os.remove(tsv)
                    write_topics_index()
                    st.warning(f"Deleted {fname}")
                    st.rerun()
    else:
        st.info("No flashcard sets yet.")
with tab2:
    json_files = [
        p for p in glob.glob(os.path.join(BUILD_DIR, "*.json"))
        if os.path.basename(p) not in ("cards.json", "topics.json")
    ]
    if not json_files:
        st.info("No flashcard sets found. Please upload notes first in ‘Manage Flashcards’.")
    else:
        all_cards = []
        for path in json_files:
            topic_name = os.path.splitext(os.path.basename(path))[0]
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("cards", []):
                c["topic"] = topic_name
            all_cards.extend(data.get("cards", []))

        # Load HTML template
        with open("static/study.html", "r", encoding="utf-8") as f:
            html_template = f.read()

        cards_json = json.dumps(all_cards, ensure_ascii=False)

        html = html_template \
        .replace("__CARDS__", cards_json) \
        .replace("__API_TOKEN__", API_TOKEN) \
        .replace("__API_BASE__", os.getenv("RECALLKIT_API_BASE", "http://localhost:8502/api"))


        components.html(html, height=1000, scrolling=True)


with tab3:
    st.header("Welcome to RecallKit 🧠")
    st.markdown("""
    **RecallKit** turns your Markdown notes into interactive flashcards with spaced repetition.

    ### 📂 Manage Flashcards
    - Upload `.md` files grouped by *topic name*.
    - Flashcards are auto-parsed into JSON + TSV.
    - You can delete or replace topics at any time.

    ### 🎓 Study
    - Select a topic (or "All").
    - Filter by tags if present.
    - Flip cards, reveal answers, and mark *Again / Hard / Good / Easy*.
    - Your progress is saved in your browser (localStorage).

    ### ⬇️ Export
    - Download generated files:
      - **JSON** → reuse in other tools
      - **TSV** → import into Quizlet

    ### 📝 Notes
    - Markdown + LaTeX are supported.
    - Multiple topics are kept independent.
    - No server database: progress stays on your device.

    ---
    **Tip:** Best experienced on desktop or iPad browsers.
    """)
