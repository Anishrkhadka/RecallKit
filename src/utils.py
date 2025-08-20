import re
import pathlib
import json
import os
import glob


# Load environment config
API_TOKEN = os.getenv("RECALLKIT_API_TOKEN", "")
DATA_DIR = os.getenv("RECALLKIT_DATA_DIR", "/app/data/progress")
BUILD_DIR = "static/web/build" 


def parse_flashcards(md_text):
    """Parse flashcards from a markdown string.

    This function scans a markdown text for sections that match the expected 
    flashcard format. Each flashcard must contain a title, a question, and an 
    answer. The function returns all valid flashcards found.

    Args:
        md_text (str): The markdown text containing flashcards.

    Returns:
        list[dict]: A list of flashcards. Each flashcard is represented as a 
            dictionary with the following keys:
            - "q" (str): The flashcard question.
            - "a" (str): The flashcard answer.
            - "title" (str): The flashcard title extracted from the heading.

    Example:
        >>> md_text = '''
        ... ## Flashcard 1: Python Basics
        ... - **Question**: What is Python?
        ... - **Answer**:
        ... A programming language.
        ... '''
        >>> parse_flashcards(md_text)
        [{'q': 'What is Python?', 'a': 'A programming language.', 'title': 'Python Basics'}]
    """
    FLASH_HEAD = re.compile(r"^#{2,6}\s*Flashcard\s*\d+\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    QUESTION_LINE = re.compile(r"^\s*[\*\-]\s+\*\*Question\*\*\s*:\s*(.+)$", re.IGNORECASE)
    ANSWER_LINE = re.compile(r"^\s*[\*\-]\s+\*\*Answer\*\*\s*:?\s*$", re.IGNORECASE)

    cards = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        m = FLASH_HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        q, a_lines = None, []
        i += 1
        while i < len(lines):
            if FLASH_HEAD.match(lines[i]) or re.match(r"^\s*---\s*$", lines[i]):
                break
            qmatch = QUESTION_LINE.match(lines[i])
            if qmatch:
                q = qmatch.group(1).strip()
            if ANSWER_LINE.match(lines[i]):
                i += 1
                while i < len(lines):
                    if FLASH_HEAD.match(lines[i]) or re.match(r"^\s*---\s*$", lines[i]):
                        break
                    a_lines.append(lines[i])
                    i += 1
                break
            i += 1
        answer = "\n".join(a_lines).strip()
        if q and answer:
            cards.append({"q": q, "a": answer, "title": title})
    return cards


def build_outputs(md_files):
    """Build structured outputs from markdown flashcards.

    Given a list of markdown files (filename and content), this function 
    extracts flashcards using `parse_flashcards` and produces three 
    different outputs:
      - JSON string containing all flashcards
      - Quizlet-compatible TSV string (tab-separated question/answer pairs)
      - Raw list of flashcard dictionaries

    Args:
        md_files (list[tuple[str, str]]): A list of tuples, where each tuple 
            contains:
            - fname (str): The markdown file name.
            - text (str): The markdown content of the file.

    Returns:
        tuple:
            - str: JSON string of all flashcards.
            - str: TSV string formatted for Quizlet (Q <tab> A).
            - list[dict]: Raw list of flashcards with keys:
                - "q" (str): The flashcard question.
                - "a" (str): The flashcard answer.
                - "title" (str): The flashcard title.
                - "tag" (str): The source filename stem (used as a tag).

    Example:
        >>> md_files = [("notes.md", "## Flashcard 1: Sample\\n- **Question**: Q?\\n- **Answer**:\\nA.")]
        >>> build_outputs(md_files)
        ('{\\n  "cards": [\\n    {\\n      "q": "Q?",\\n      "a": "A.",\\n      "title": "Sample",\\n      "tag": "notes"\\n    }\\n  ]\\n}', 
         'Q?\\tA.\\n', 
         [{'q': 'Q?', 'a': 'A.', 'title': 'Sample', 'tag': 'notes'}])
    """
    cards = []
    for fname, text in md_files:
        cs = parse_flashcards(text)
        for c in cs:
            c["tag"] = pathlib.Path(fname).stem
        cards.extend(cs)

    cards_json = json.dumps({"cards": cards}, ensure_ascii=False, indent=2)

    quizlet_tsv = ""
    for c in cards:
        quizlet_tsv += f"{c['q']}\t{c['a']}\n"

    return cards_json, quizlet_tsv, cards


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