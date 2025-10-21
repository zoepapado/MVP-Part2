
from __future__ import annotations
import datetime as dt
from db import init_db, SessionLocal, User, Project, Quest
from utils import mk_slug

def seed():
    init_db()
    db = SessionLocal()
    founder = User(email="founder@demo.io", password="demo", role="founder", name="Demo Founder")
    critic  = User(email="critic@demo.io",  password="demo", role="critic",  name="Demo Critic")
    db.add_all([founder, critic]); db.commit()

    # Huel example
    huel = Project(
        owner_id=founder.id,
        name="Huel — DTC Storefront & Conversion",
        slug=mk_slug("Huel DTC Storefront"),
        description="Evaluate first-time buyer flow, subscription clarity, and PDP-to-checkout funnel for Huel.",
        url="https://huel.com",
        tags=["nutrition","dtc","subscription","checkout"]
    )
    db.add(huel); db.commit()

    q1 = Quest(
        project_id=huel.id, title="First-time buyer journey",
        brief="As a new customer, go from landing page to checkout. Identify friction points (copy, images, sizing, flavour choices) and propose fixes.",
        tags=["onboarding","pdp","checkout","copy"],
        reward_type="points", reward_value=30,
        deadline=dt.datetime.utcnow() + dt.timedelta(days=7)
    )
    q2 = Quest(
        project_id=huel.id, title="Subscription UX & pricing clarity",
        brief="Is the subscription toggle obvious? Are savings and delivery cadence crystal clear? Suggest UI copy & layout improvements.",
        tags=["subscription","pricing","toggle","clarity"],
        reward_type="points", reward_value=25,
        deadline=dt.datetime.utcnow() + dt.timedelta(days=10)
    )
    db.add_all([q1, q2]); db.commit()
    db.close()
    print("Seeded demo data (Huel).")

if __name__ == "__main__":
    seed()
