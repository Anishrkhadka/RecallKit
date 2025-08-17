# 📚 RecallKit

RecallKit turns your Markdown notes into interactive flashcards with **spaced repetition**.  

Your `.md` sections look like this:

```markdown
---
### Flashcard N: Title
* **Question**: What is ... ?
* **Answer**:
    * bullet points
    * formulas: $$ y = ax + b $$
---
```

## 🚀 How to Use

### 1. Run with Docker (recommended)

```bash
docker build -t study-site .
docker run -p 8501:8501 study-site
```

Then open [http://localhost:8501](http://localhost:8501) in your browser or iPad.

---

### 2. Upload & Manage

* Go to **📂 Manage Flashcards** tab.
* Enter a topic name (e.g. `time_series`) and upload one or more `.md` files.
* Flashcards are parsed and saved into `web/build/<topic>.json` + `<topic>.tsv`.
* You can delete sets individually.

---

### 3. Study

* Switch to the **🎓 Study** tab.
* Choose a topic (or “All”) and optionally filter by tag.
* Use the interface to flip cards, reveal answers, and mark *Again / Hard / Good / Easy*.
* Progress is tracked with a simple Leitner-style system stored in your browser (localStorage).

---

### 4. Optional Exports

* Download flashcards as:

  * `cards.json` (for re-use)
  * `quizlet.tsv` (import into Quizlet)

---

## 📝 Notes

* Supports **Markdown** rendering and **LaTeX formulas** (via KaTeX).
* Each topic is independent, so you can keep multiple subjects (e.g. *maths*, *time series*, *statistics*).
* No server-side DB — progress is stored per-device in your browser.
