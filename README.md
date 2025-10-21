
# IterRate (MVP v2) — Streamlit + SQLite

A functional prototype of **IterRate** — a two-sided, gamified product-feedback marketplace with AI-assisted clustering and actionable summaries.

**New in v2**
- Huel demo project with quests
- Click-through **Visit site** link on projects
- Nicer UI (cards + hero) and a **Reset demo DB** button
- Theme via `.streamlit/config.toml`

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
streamlit run app.py
```
Demo accounts: founder@demo.io / demo, critic@demo.io / demo
