
from __future__ import annotations
from slugify import slugify

def mk_slug(name: str) -> str:
    return slugify(name)

def sample_badges(points: int) -> list[str]:
    badges = []
    if points >= 50: badges.append("Contributor")
    if points >= 200: badges.append("Pro Reviewer")
    if points >= 500: badges.append("Hall of Fame")
    return badges

def reward_points(quality: float, reward_value: float) -> int:
    base = reward_value
    mult = 0.5 + 1.5 * quality
    return int(base * mult)
