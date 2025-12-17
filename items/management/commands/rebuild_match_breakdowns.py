from django.core.management.base import BaseCommand
from items.models import Match
from items.matching import item_score_breakdown

class Command(BaseCommand):
    help = "Rebuild score_breakdown for all matches"

    def handle(self, *args, **opts):
        updated = 0
        for m in Match.objects.select_related("lost_item", "found_item"):
            bd = item_score_breakdown(m.lost_item, m.found_item)
            m.score = bd["total"]
            m.score_breakdown = bd
            m.save(update_fields=["score", "score_breakdown"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} matches"))
