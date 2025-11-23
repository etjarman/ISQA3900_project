from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model

from items.models import Item, Category
from items.matching import item_score, find_matches_for

User = get_user_model()


class MatchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="testpass123",
        )

        self.electronics = Category.objects.create(name="Electronics")
        self.clothing = Category.objects.create(name="Clothing")

        base_date = date.today()

        # LOST laptop in Mammel Hall – our main "lost" item
        self.lost_laptop = Item.objects.create(
            owner=self.user,
            status="LOST",
            title="Silver Dell laptop",
            description="Lost in Mammel Hall classroom 110",
            category=self.electronics,
            color_primary="Silver",
            brand="Dell",
            model_or_markings="Latitude 5400",
            building="Mammel Hall",
            room_or_area="MH 110",
            date_lost_or_found=base_date,
            approved=True,
        )

        # FOUND laptop – should be a strong match
        self.found_laptop = Item.objects.create(
            owner=self.user,
            status="FOUND",
            title="Dell silver laptop",
            description="Found in MH 110 near back row.",
            category=self.electronics,
            color_primary="Silver",
            brand="Dell",
            model_or_markings="Latitude",
            building="Mammel Hall",
            room_or_area="MH 110",
            date_lost_or_found=base_date + timedelta(days=1),
            approved=True,
        )

        # FOUND jacket – different category, should NOT match
        self.found_jacket = Item.objects.create(
            owner=self.user,
            status="FOUND",
            title="Black jacket",
            description="Left in Mammel lobby",
            category=self.clothing,
            color_primary="Black",
            brand="North Face",
            building="Mammel Hall",
            room_or_area="Lobby",
            date_lost_or_found=base_date,
            approved=True,
        )

        # FOUND laptop, but UNAPPROVED – should only show up when include_unapproved=True
        self.found_unapproved = Item.objects.create(
            owner=self.user,
            status="FOUND",
            title="Silver Dell laptop",
            description="Found somewhere in Mammel",
            category=self.electronics,
            color_primary="Silver",
            brand="Dell",
            model_or_markings="Latitude",
            building="Mammel Hall",
            room_or_area="MH 110",
            date_lost_or_found=base_date,
            approved=False,
        )

    def test_score_is_high_for_good_match(self):
        """Good LOST/FOUND pair should have score >= 40."""
        score = item_score(self.lost_laptop, self.found_laptop)
        self.assertGreaterEqual(
            score, 40.0,
            f"Expected strong match score >= 40, got {score}"
        )

    def test_find_matches_returns_good_candidate(self):
        """find_matches_for should include the correct FOUND item."""
        matches = find_matches_for(self.lost_laptop)
        candidates = [m[0] for m in matches]

        self.assertIn(self.found_laptop, candidates)
        self.assertNotIn(
            self.found_jacket,
            candidates,
            "Item from different category should not match",
        )

    def test_unapproved_items_excluded_by_default(self):
        """Unapproved items should not be suggested unless include_unapproved=True."""
        matches = find_matches_for(self.lost_laptop)
        candidates = [m[0] for m in matches]
        self.assertNotIn(
            self.found_unapproved,
            candidates,
            "Unapproved item appeared without include_unapproved=True",
        )

    def test_include_unapproved_flag_includes_unapproved(self):
        """include_unapproved=True should allow matching against unapproved items."""
        matches = find_matches_for(self.lost_laptop, include_unapproved=True)
        candidates = [m[0] for m in matches]
        self.assertIn(
            self.found_unapproved,
            candidates,
            "Unapproved item was not included with include_unapproved=True",
        )

    def test_does_not_match_same_status(self):
        """LOST should not match other LOST items."""
        # If find_matches_for is written correctly, candidates for a LOST item
        # will all be FOUND items.
        matches = find_matches_for(self.lost_laptop)
        for candidate, score in matches:
            self.assertEqual(
                candidate.status,
                "FOUND",
                "Matching LOST item should only return FOUND items",
            )

    def test_claimed_item_produces_no_candidates(self):
        """CLAIMED items should not try to find new matches."""
        self.lost_laptop.status = "CLAIMED"
        self.lost_laptop.save()

        matches = find_matches_for(self.lost_laptop)
        self.assertEqual(
            len(matches),
            0,
            "CLAIMED item still produced matches",
        )

    def test_matching_is_case_insensitive(self):
        """Differences in case should not affect matching."""
        self.found_laptop.title = "dell SILVER Laptop"
        self.found_laptop.color_primary = "silver"
        self.found_laptop.brand = "DELL"
        self.found_laptop.save()

        score = item_score(self.lost_laptop, self.found_laptop)
        self.assertGreaterEqual(
            score, 40.0,
            f"Case differences lowered the score too much: {score}",
        )
