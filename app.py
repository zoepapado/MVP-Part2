
from __future__ import annotations
import os, datetime as dt
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from db import init_db, SessionLocal, User, Project, Quest, Feedback, ClusterSummary
from ai import sentiment_score, grade_quality, cluster_feedback, do_next_cards, instant_fix_suggestions
from utils import mk_slug, reward_points, sample_badges

Session = init_db()
st.set_page_config(page_title="IterRate — MVP", page_icon="🚀", layout="wide")

# ---- Global CSS (cards + hero) ----
st.markdown("""
<style>
.hero {
  padding: 2rem 2.2rem; border-radius: 18px;
  background: linear-gradient(135deg,#e0f2fe 0%, #f5f3ff 100%);
  border: 1px solid #e6e9ef;
}
.card {
  padding: 1rem 1.1rem; border-radius: 14px; border: 1px solid #e6e9ef;
  background: #fff; box-shadow: 0 1px 2px rgba(10, 20, 30, 0.04);
  margin-bottom: 12px;
}
.badge { display:inline-block; padding:2px 8px; border-radius:999px;
  background:#eef2ff; color:#4338ca; font-size:12px; margin-right:6px; }
.project-title{ font-weight:600; font-size:1.05rem; margin-bottom:2px;}
.smallmuted{ color:#64748b; font-size:0.9rem; }
a.visit { text-decoration:none; background:#0ea5e9; color:white; padding:6px 10px; border-radius:10px; }
</style>
""", unsafe_allow_html=True)

# ---- Auth ----
def login_box():
    st.sidebar.header("Sign in")
    email = st.sidebar.text_input("Email", value=st.session_state.get("email",""))
    pw = st.sidebar.text_input("Password", type="password", value=st.session_state.get("pw",""))
    role = st.sidebar.selectbox("Role", ["founder", "critic"], index=0)
    if st.sidebar.button("Log in"):
        db = Session()
        user = db.query(User).filter_by(email=email, password=pw, role=role).first()
        if not user:
            st.sidebar.error("Invalid credentials. Try the demo accounts in README.")
        else:
            st.session_state["user_id"] = user.id
            st.session_state["role"] = user.role
            st.session_state["email"] = email
            st.session_state["pw"] = pw
            st.rerun()
        db.close()

def ensure_seed():
    db = Session()
    if db.query(User).count() == 0:
        import seed; seed.seed()
    db.close()

ensure_seed()

# ---- Optional: reset DB for demo ----
with st.sidebar.expander("⚙️ Admin / Demo tools"):
    if st.button("Reset demo database"):
        try:
            db = Session(); db.close()
            if os.path.exists("iterate.db"):
                os.remove("iterate.db")
            import seed; seed.seed()
            st.success("Database reset & reseeded.")
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")

if "user_id" not in st.session_state:
    st.markdown("""<div class='hero'>
    <h2>IterRate — Feedback that builds better products, faster.</h2>
    <p class='smallmuted'>Create feedback quests, crowdsource insights, auto-cluster issues, and get action cards.</p>
    </div>""", unsafe_allow_html=True)
    login_box()
    st.stop()

db = Session()
me = db.query(User).get(st.session_state["user_id"])

st.sidebar.write(f"Signed in as **{me.name or me.email}** ({me.role})")
page = st.sidebar.radio("Navigate", ["Home", "Projects", "Quests", "Feedback", "Insights", "Leaderboards", "Raids"])

def render_health_gauge(project_id: int):
    N = 200
    fb = db.query(Feedback).join(Quest).filter(Quest.project_id==project_id).order_by(Feedback.created_at.desc()).limit(N).all()
    if not fb:
        st.info("No feedback yet for health gauge.")
        return
    avg_sent = sum(f.sentiment for f in fb)/len(fb)
    density = min(1.0, len(fb)/N)
    health = round(50 + 50*avg_sent * density, 1)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health,
        gauge={'axis': {'range': [0,100]}, 'bar': {'thickness': 0.3}},
        title={'text': "Impact Meter (Site Health)"}
    ))
    st.plotly_chart(fig, use_container_width=True)

# ---- Pages ----
if page == "Home":
    st.markdown("""<div class='hero'>
    <h2>Welcome back 👋</h2>
    <p class='smallmuted'>Pick a project, launch a raid, or cluster fresh feedback.</p>
    </div>""", unsafe_allow_html=True)
    st.write("")
    st.subheader("Live Projects")

    projects = db.query(Project).all()
    if not projects:
        st.info("No projects yet.")
    for p in projects:
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            cols = st.columns([6,2])
            with cols[0]:
                st.markdown(f"<div class='project-title'>{p.name}</div>", unsafe_allow_html=True)
                tags = " ".join([f"<span class='badge'>{t}</span>" for t in (p.tags or [])])
                st.markdown(tags, unsafe_allow_html=True)
                st.markdown(f"<div class='smallmuted'>{p.description or '—'}</div>", unsafe_allow_html=True)
            with cols[1]:
                if p.url:
                    st.markdown(f"<p style='text-align:right'><a class='visit' href='{p.url}' target='_blank'>Visit site ↗</a></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            render_health_gauge(p.id)

elif page == "Projects":
    st.header("Projects")
    if me.role == "founder":
        with st.form("new_proj"):
            name = st.text_input("Project name")
            desc = st.text_area("Description")
            url = st.text_input("Website (optional)")
            tags = st.text_input("Tags (comma-separated)", value="ux,website")
            if st.form_submit_button("Create"):
                if not name.strip():
                    st.error("Name required.")
                else:
                    pr = Project(owner_id=me.id, name=name, slug=mk_slug(name), description=desc, url=url or None, tags=[t.strip() for t in tags.split(",") if t.strip()])
                    db.add(pr); db.commit(); st.success("Project created.")
        st.write("---")

    projs = db.query(Project).all() if me.role=="critic" else db.query(Project).filter_by(owner_id=me.id).all()
    if not projs:
        st.info("No projects yet.")
    for p in projs:
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            cols = st.columns([6,2])
            with cols[0]:
                st.markdown(f"<div class='project-title'>{p.name}</div>", unsafe_allow_html=True)
                st.markdown(" ".join([f"<span class='badge'>{t}</span>" for t in (p.tags or [])]), unsafe_allow_html=True)
                st.markdown(f"<div class='smallmuted'>{p.description or '—'}</div>", unsafe_allow_html=True)
            with cols[1]:
                if p.url:
                    st.markdown(f"<p style='text-align:right'><a class='visit' href='{p.url}' target='_blank'>Visit site ↗</a></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "Quests":
    st.header("Feedback Quests")
    if me.role == "founder":
        my_projects = db.query(Project).filter_by(owner_id=me.id).all()
        if not my_projects:
            st.info("Create a project first.")
        else:
            with st.form("new_quest"):
                proj = st.selectbox("Project", my_projects, format_func=lambda p: p.name)
                title = st.text_input("Title")
                brief = st.text_area("Brief / acceptance criteria")
                tags = st.text_input("Tags (comma-separated)", value="onboarding,ux")
                reward_type = st.selectbox("Reward type", ["points","cash","token","perk","charity"])
                reward_val = st.number_input("Reward value", min_value=1.0, value=15.0, step=1.0)
                deadline = st.date_input("Deadline", value=dt.date.today() + dt.timedelta(days=7))
                if st.form_submit_button("Create Quest"):
                    q = Quest(project_id=proj.id, title=title, brief=brief,
                              tags=[t.strip() for t in tags.split(",") if t.strip()],
                              reward_type=reward_type, reward_value=reward_val,
                              deadline=dt.datetime.combine(deadline, dt.time(23,59)))
                    db.add(q); db.commit(); st.success("Quest created.")

    quests = db.query(Quest).all() if me.role=="critic" else db.query(Quest).join(Project).filter(Project.owner_id==me.id).all()
    for q in quests:
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader(q.title)
            st.caption(f"Tags: {', '.join(q.tags or [])} · Deadline: {q.deadline.date() if q.deadline else '—'} · Reward: {q.reward_value} {q.reward_type}")
            st.write(q.brief or "—")
            if me.role == "critic" and q.status in ("open","active"):
                with st.form(f"fb_{q.id}"):
                    text = st.text_area("Your feedback", height=140, key=f"fbtext{q.id}")
                    if st.form_submit_button("Submit feedback"):
                        if not text.strip():
                            st.error("Please enter feedback.")
                        else:
                            s = sentiment_score(text)
                            g = grade_quality(text)
                            fixes = instant_fix_suggestions(text)
                            fb = Feedback(quest_id=q.id, critic_id=me.id, text=text, sentiment=s,
                                          specificity=g["specificity"], helpfulness=g["helpfulness"],
                                          quality_score=g["quality"], suggestions=fixes)
                            db.add(fb); db.commit()
                            pts = reward_points(g["quality"], q.reward_value)
                            me.points += pts
                            me.badges = sample_badges(me.points)
                            db.commit()
                            st.success(f"Submitted. Earned {pts} points.")
            if me.role == "founder":
                feed = db.query(Feedback).filter_by(quest_id=q.id).order_by(Feedback.created_at.desc()).all()
                if feed:
                    df = pd.DataFrame([{
                        "critic": f"#{f.critic_id}",
                        "sent": round(f.sentiment,2),
                        "spec": round(f.specificity,2),
                        "help": round(f.helpfulness,2),
                        "quality": round(f.quality_score,2),
                        "suggestions": "; ".join(f.suggestions or []),
                        "text": f.text[:160] + ("…" if len(f.text)>160 else "")
                    } for f in feed])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    if st.button(f"Cluster & Summarize (quest #{q.id})"):
                        texts = [f.text for f in feed]
                        res = cluster_feedback(texts, k=min(6, max(2, len(texts)//3 or 2)))
                        for f, label in zip(feed, res["labels"]):
                            f.cluster_id = int(label)
                        db.commit()
                        cards = do_next_cards(res["top_terms"])
                        st.success("Clusters computed.")
                        for c in cards:
                            st.info(f"**{c['title']}**\n{c['action']}\nImpact: {c['impact']} · Effort: {c['effort']}")
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "Feedback":
    st.header("My Feedback")
    my_fb = db.query(Feedback).filter_by(critic_id=me.id).order_by(Feedback.created_at.desc()).all()
    if not my_fb:
        st.info("You haven't submitted feedback yet.")
    else:
        for f in my_fb:
            with st.expander(f"Quest #{f.quest_id} · quality {round(f.quality_score,2)} · sent {round(f.sentiment,2)}"):
                st.write(f.text)
                if f.suggestions:
                    st.caption("Instant Fix-It: " + "; ".join(f.suggestions))

elif page == "Insights":
    st.header("Insights — Live")
    if me.role != "founder":
        st.info("Insights are for founders. Submit feedback to climb the leaderboard!")
    else:
        my_projects = db.query(Project).filter_by(owner_id=me.id).all()
        if not my_projects:
            st.info("Create a project first.")
        else:
            p = st.selectbox("Project", my_projects, format_func=lambda x: x.name)
            st.subheader("Impact Meter")
            render_health_gauge(p.id)
            all_fb = db.query(Feedback).join(Quest).filter(Quest.project_id==p.id).all()
            if st.button("Recompute clusters across project"):
                texts = [f.text for f in all_fb]
                res = cluster_feedback(texts, k=min(8, max(2, len(texts)//4 or 2)))
                for f, label in zip(all_fb, res["labels"]):
                    f.cluster_id = int(label)
                db.commit()
                cards = do_next_cards(res["top_terms"])
                st.success("Project clusters updated.")
                for c in cards:
                    st.info(f"**{c['title']}**\n{c['action']}\nImpact: {c['impact']} · Effort: {c['effort']}")

elif page == "Leaderboards":
    st.header("Leaderboards")
    critics = db.query(User).filter_by(role="critic").order_by(User.points.desc()).all()
    if not critics:
        st.info("No critics yet. Encourage signups!")
    else:
        df = pd.DataFrame([{"critic": c.name or c.email, "points": c.points, "streak": c.streak, "badges": ", ".join(c.badges or [])} for c in critics])
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Raids":
    st.header("Feedback Raids (sprints)")
    st.write("Schedule a 30-minute sprint to gather 10+ reviews fast. Demo only.")
    if me.role == "founder":
        with st.form("raid_form"):
            title = st.text_input("Raid name", value="Honest Hour — Onboarding")
            when = st.date_input("Date", value=dt.date.today() + dt.timedelta(days=1))
            time = st.time_input("Time", value=dt.time(17, 0))
            min_reviewers = st.number_input("Min reviewers", 5, 50, 10)
            reward_boost = st.slider("Reward boost ×", 1.0, 3.0, 1.5, 0.1)
            if st.form_submit_button("Create Raid"):
                st.success(f"Raid scheduled: {title} on {when} at {time}. Reward boost ×{reward_boost}. (Demo)")

st.sidebar.write("---")
if st.sidebar.button("Sign out"):
    for k in ["user_id","role","email","pw"]:
        st.session_state.pop(k, None)
    st.rerun()
