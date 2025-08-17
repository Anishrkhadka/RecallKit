import re, pathlib, json, csv

def parse_flashcards(md_text):
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
