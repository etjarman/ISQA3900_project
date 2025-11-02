import re
from difflib import SequenceMatcher
from datetime import timedelta
from django.utils import timezone
from .models import Item
WORD_RE = re.compile(r'[a-z0-9]+')
def norm(s): return WORD_RE.findall((s or '').lower())

def jaccard(a,b): A,B=set(a),set(b); return (len(A&B)/len(A|B)) if (A or B) else 0.0

def fuzzy(a,b): return SequenceMatcher(None,(a or '').lower(),(b or '').lower()).ratio()

def days_prox(a,b,max_days=30):
    if not a or not b: return 0.0
    d = abs((a-b).days)
    return max(0.0, 1 - d/max_days)

def candidate_queryset(new_item):
    base = new_item.date_lost_or_found or timezone.now().date()
    start, end = base - timedelta(days=30), base + timedelta(days=30)
    opposite = "FOUND" if new_item.status == "LOST" else "LOST"
    qs = Item.objects.filter(
        status=("FOUND" if new_item.status == "LOST" else "LOST"),
        category=new_item.category,
        date_lost_or_found__range=(start, end),
    )
    if not include_unapproved:
        qs = qs.filter(approved=True)
    if new_item.building:
        qs = qs.filter(building__iexact=new_item.building)
    return qs.order_by("-date_reported")[:50]

def item_score(a,b):
    s = 0.0
    if (a.building or '').lower() == (b.building or '').lower(): s += 20
    if a.color_primary and b.color_primary and a.color_primary.lower()==b.color_primary.lower(): s += 15
    s += 25*max(jaccard(norm(a.brand),norm(b.brand)), jaccard(norm(a.model_or_markings),norm(b.model_or_markings)))
    s += 20*max(fuzzy(a.title,b.title), fuzzy(a.description,b.description))
    s += 10*days_prox(a.date_lost_or_found, b.date_lost_or_found)
    s += 10*jaccard(norm(a.room_or_area), norm(b.room_or_area))
    return round(s,1)

def find_matches_for(new_item, include_unapproved=False):
    return [
        (c, item_score(new_item, c))
        for c in candidate_queryset(new_item, include_unapproved=include_unapproved)
        if item_score(new_item, c) >= 40
    ]