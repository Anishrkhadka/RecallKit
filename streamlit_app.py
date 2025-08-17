import os, glob, json
import streamlit as st
import streamlit.components.v1 as components
import parser
import json


BUILD_DIR = "static/web/build" 

st.set_page_config(page_title="RecallKit", layout="wide")

tab1, tab2 = st.tabs(["📂 Manage Flashcards", "🎓 Study"])

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
    # st.header("Study Mode")

    # 1) Collect cards from all topics
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
                c["topic"] = topic_name  # tag card with its topic
            all_cards.extend(data.get("cards", []))

        # 2) Inline assets (CSS) – if you already have these files, great; otherwise keep as-is
        style_css = ""
        css_path = os.path.join("web", "style.css")
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                style_css = f.read()
        else:
            # tiny fallback so it still looks reasonable
            style_css = """
            body{font-family:-apple-system,system-ui,Segoe UI,Roboto;margin:0}
            main{max-width:900px;margin:0 auto;padding:16px}
            h1{font-size:22px;margin:8px 0}
            .controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
            .card{border:1px solid #ddd;border-radius:14px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
            .title{font-weight:600;margin-bottom:8px}
            .q,.a{font-size:18px;line-height:1.6;word-wrap:break-word}
            button{padding:8px 12px;border-radius:10px;border:1px solid #cfcfcf;background:#fff}
            select{padding:6px 10px;border-radius:8px;border:1px solid #cfcfcf}
            hr{border:none;border-top:1px solid #eee;margin:10px 0}
            .leitner{display:flex;gap:8px;margin-top:12px}
            """

        # 3) Build the full HTML (Showdown + MathJax + our JS app), injecting CARDS
        html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Study Cards</title>
  <style>{style_css}</style>

  <!-- Showdown for Markdown -->
  <script src="https://cdn.jsdelivr.net/npm/showdown@2.1.0/dist/showdown.min.js"></script>

  <!-- MathJax for LaTeX -->
  <script>
  window.MathJax = {{
    tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] }},
    svg: {{ fontCache: 'global' }}
  }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>

  <script>
  // Injected data from Streamlit
  const CARDS = {{ "cards": {json.dumps(all_cards, ensure_ascii=False)} }};
  </script>

</head>
<body>
  <main>
    <header>
      <h1>Study Cards</h1>
      <div class="controls">
        <select id="topic"></select>
        <select id="tag"></select>
        <button id="prev">Prev</button>
        <button id="show">Show / Hide</button>
        <button id="next">Next</button>
      </div>
    </header>

    <section class="card">
      <div class="title" id="title"></div>
      <div class="q" id="q"></div>
      <hr/>
      <div class="a" id="a" style="display:none"></div>
      <div class="leitner">
        <button id="again">Again</button>
        <button id="hard">Hard</button>
        <button id="good">Good</button>
        <button id="easy">Easy</button>
      </div>
    </section>
    <footer><small>Progress is saved locally in this browser (per-device).</small></footer>
  </main>

  <script>
  // === app.js logic (adapted to use CARDS instead of fetch) ===
  let cards=[], queue=[], idx=0, shown=false;

  const fmt = new showdown.Converter({{
    tables: true,
    strikethrough: true,
    ghCodeBlocks: true,
    literalMidWordUnderscores: true,
    simpleLineBreaks: true
  }});

  // Preserve LaTeX so MathJax can render it
  fmt.addExtension(() => [{{
    type: 'lang',
    regex: /\\$\\$[^]*?\\$\\$|\\$[^$]+\\$/g,
    replace: (m) => m
  }}]);

  function idOf(c){{ return (c.topic||"default")+"::"+(c.tag||"")+"::"+(c.title||"")+"::"+c.q; }}

  function loadProgress() {{
    try {{ return JSON.parse(localStorage.getItem("leitner")||"{{}}"); }} catch {{ return {{}}; }}
  }}
  function saveProgress(state) {{ localStorage.setItem("leitner", JSON.stringify(state)); }}
  let prog = loadProgress(); // {{id: {{box,last}}}}

  function schedule(box){{ return [0,0,1,3,7,16,35][Math.min(box,6)]; }}

  function render() {{
    if(queue.length===0){{
      document.getElementById("title").textContent="";
      document.getElementById("q").textContent="No cards.";
      document.getElementById("a").textContent="";
      return;
    }}
    const c = queue[idx];
    document.getElementById("title").textContent = (c.topic ? `[${{c.topic}}] ` : "") + (c.title||"");
    document.getElementById("q").innerHTML = fmt.makeHtml(c.q);
    document.getElementById("a").innerHTML = fmt.makeHtml(c.a);
    document.getElementById("a").style.display = shown ? "block" : "none";
    if (window.MathJax && window.MathJax.typeset) window.MathJax.typeset();
  }}

  function move(d){{ if(queue.length){{ idx=(idx+d+queue.length)%queue.length; shown=false; render(); }} }}

  function grade(quality){{
    if(!queue.length) return;
    const c = queue[idx]; const id = idOf(c);
    const st = prog[id] || {{box:1,last:0}};
    if(quality==="again") st.box=1;
    else if(quality==="hard") st.box=Math.max(1, st.box);
    else if(quality==="good") st.box=Math.min(6, st.box+1);
    else if(quality==="easy") st.box=Math.min(6, st.box+2);
    st.last = Date.now();
    prog[id]=st; saveProgress(prog);
    move(1);
  }}

  function updateTagOptions(){{
    const topicSel = document.getElementById("topic").value;
    const tagEl = document.getElementById("tag");
    const visible = cards.filter(c => !topicSel || c.topic===topicSel);
    const tags = [...new Set(visible.map(c=>c.tag))].filter(Boolean).sort();
    tagEl.innerHTML = `<option value="">All</option>` + tags.map(t=>`<option>${{t}}</option>`).join("");
  }}

  function applyFilters(){{
    const topicSel = document.getElementById("topic").value;
    const tagSel = document.getElementById("tag").value;
    const now = Date.now();
    const filtered = cards.filter(c => (!topicSel || c.topic===topicSel) && (!tagSel || c.tag===tagSel));
    let due = filtered.filter(c => {{
      const st = prog[idOf(c)] || {{box:1,last:0}};
      const dueTime = st.last + schedule(st.box)*86400*1000;
      return dueTime <= now;
    }});
    if(due.length===0) due = filtered.slice();
    queue = due; idx=0; shown=false; render();
  }}

  function boot(){{
    // Load from injected CARDS
    cards = (CARDS.cards || []).slice();
    // Topic dropdown
    const topicEl = document.getElementById("topic");
    const topics = [...new Set(cards.map(c=>c.topic||"default"))].sort();
    topicEl.innerHTML = `<option value="">All</option>` + topics.map(t=>`<option>${{t}}</option>`).join("");
    updateTagOptions();
    applyFilters();
  }}

  // Wire up controls
  document.getElementById("prev").onclick = () => move(-1);
  document.getElementById("next").onclick = () => move(1);
  document.getElementById("show").onclick = () => {{ shown=!shown; render(); }};
  document.getElementById("again").onclick = () => grade("again");
  document.getElementById("hard").onclick  = () => grade("hard");
  document.getElementById("good").onclick  = () => grade("good");
  document.getElementById("easy").onclick  = () => grade("easy");
  document.getElementById("topic").onchange = () => {{ updateTagOptions(); applyFilters(); }};
  document.getElementById("tag").onchange   = applyFilters;

  // Start
  boot();
  </script>
</body>
</html>
        """

        # 4) Render inside Streamlit
        components.html(html, height=900, scrolling=True)
