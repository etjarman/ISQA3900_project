import re
from difflib import SequenceMatcher
from datetime import timedelta

from django.utils import timezone

from .models import Item

WORD_RE = re.compile(r"[a-z0-9]+")


def norm(s):
    return WORD_RE.findall((s or "").lower())


def jaccard(a, b):
    A, B = set(a), set(b)
    return (len(A & B) / len(A | B)) if (A or B) else 0.0


def fuzzy(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def days_prox(a, b, max_days=30):
    """0–1 score based on how close the dates are."""
    if not a or not b:
        return 0.0
    d = abs((a - b).days)
    return max(0.0, 1 - d / max_days)


def candidate_queryset(new_item, include_unapproved=False):
    # Only try to match LOST/FOUND.
    if new_item.status not in ("LOST", "FOUND"):
        return Item.objects.none()

    base = new_item.date_lost_or_found or timezone.now().date()
    start, end = base - timedelta(days=30), base + timedelta(days=30)
    opposite = "FOUND" if new_item.status == "LOST" else "LOST"

    qs = Item.objects.filter(
        status=opposite,
        category=new_item.category,
        date_lost_or_found__range=(start, end),
    )

    if not include_unapproved:
        qs = qs.filter(approved=True)

    if new_item.building:
        qs = qs.filter(building__iexact=new_item.building)

    return qs.order_by("-date_reported")[:50]


def item_score(a, b):
    """
    Compute a similarity score between two items.
    Typical “good match” is ≥ 40.
    """
    s = 0.0

    # Building match (strong context signal)
    if (a.building or "").lower() == (b.building or "").lower():
        s += 20

    # Exact color match
    if a.color_primary and b.color_primary and a.color_primary.lower() == b.color_primary.lower():
        s += 15

    # Brand / model Jaccard – strong but not decisive
    brand_sim = jaccard(norm(a.brand), norm(b.brand))
    model_sim = jaccard(norm(a.model_or_markings), norm(b.model_or_markings))
    s += 25 * max(brand_sim, model_sim)

    # Title / description fuzzy match
    title_sim = fuzzy(a.title, b.title)
    desc_sim = fuzzy(a.description, b.description)
    s += 20 * max(title_sim, desc_sim)

    # Date proximity (up to +10)
    s += 10 * days_prox(a.date_lost_or_found, b.date_lost_or_found)

    # Room similarity (Jaccard)
    s += 10 * jaccard(norm(a.room_or_area), norm(b.room_or_area))

    return round(s, 1)


def find_matches_for(new_item, include_unapproved=False, threshold=40.0):
    """
    Tweak threshold here
    Return list of (candidate_item, score) pairs whose score ≥ threshold.
    """
    matches = []
    for candidate in candidate_queryset(new_item, include_unapproved=include_unapproved):
        score = item_score(new_item, candidate)
        if score >= threshold:
            matches.append((candidate, score))
    return matches

def explain_match(a, b):
    """
    Return an explanation of why two items matched,
    based on the same logic used in item_score.
    """
    details = []
    total = 0.0

    # Building
    if (a.building or "").lower() == (b.building or "").lower():
        total += 20
        details.append("Same building (+20)")

    # Color
    if a.color_primary and b.color_primary and a.color_primary.lower() == b.color_primary.lower():
        total += 15
        details.append(f"Same color ({a.color_primary}) (+15)")

    # Brand / model similarity
    brand_sim = jaccard(norm(a.brand), norm(b.brand))
    model_sim = jaccard(norm(a.model_or_markings), norm(b.model_or_markings))
    brand_model_sim = max(brand_sim, model_sim)
    if brand_model_sim > 0:
        points = 25 * brand_model_sim
        total += points
        details.append(f"Brand/model similarity {brand_model_sim:.2f} (+{points:.1f})")

    # Title / description fuzzy similarity
    title_sim = fuzzy(a.title, b.title)
    desc_sim = fuzzy(a.description, b.description)
    text_sim = max(title_sim, desc_sim)
    if text_sim > 0:
        points = 20 * text_sim
        total += points
        details.append(f"Title/description similarity {text_sim:.2f} (+{points:.1f})")

    # Date proximity
    date_prox = days_prox(a.date_lost_or_found, b.date_lost_or_found)
    if date_prox > 0:
        points = 10 * date_prox
        total += points
        details.append(f"Dates close ({date_prox:.2f}) (+{points:.1f})")

    # Room / area Jaccard
    room_sim = jaccard(norm(a.room_or_area), norm(b.room_or_area))
    if room_sim > 0:
        points = 10 * room_sim
        total += points
        details.append(f"Room/area similarity {room_sim:.2f} (+{points:.1f})")

    details.append(f"Total ≈ {round(total, 1)}")

    return "; ".join(details)