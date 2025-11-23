from django.contrib import admin, messages
from django.db import transaction
from .models import Category, Item, Match, Message
from .matching import find_matches_for, explain_match
import logging

log = logging.getLogger(__name__)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']

class LostMatchInline(admin.TabularInline):
    model = Match
    fk_name = "lost_item"
    extra = 0
    can_delete = False
    readonly_fields = ("found_item", "score", "status")


class FoundMatchInline(admin.TabularInline):
    model = Match
    fk_name = "found_item"
    extra = 0
    can_delete = False
    readonly_fields = ("lost_item", "score", "status")


def approve_items(modeladmin, request, queryset):
    """
    Bulk-approve selected items and attempt to refresh matches.
    """
    items = list(queryset)

    updated = queryset.update(approved=True)

    refreshed = 0
    for item in items:
        try:
            with transaction.atomic():
                try:
                    candidates = find_matches_for(item, include_unapproved=True)
                except TypeError:
                    candidates = find_matches_for(item)

                for other, score in candidates:
                    if item.status == 'LOST':
                        Match.objects.get_or_create(
                            lost_item=item, found_item=other, defaults={'score': score}
                        )
                    else:
                        Match.objects.get_or_create(
                            lost_item=other, found_item=item, defaults={'score': score}
                        )
                refreshed += 1
        except Exception as e:
            log.exception("Match refresh failed for item %s: %s", item.pk, e)

    modeladmin.message_user(
        request,
        f"Approved {updated} item(s). Refreshed matches for {refreshed} item(s).",
        level=messages.SUCCESS,
    )

approve_items.short_description = "Approve selected items (and refresh matches)"

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id','title','status','category','owner','approved','building','date_lost_or_found','match_count')
    list_filter  = ('approved','status','category','building')
    search_fields = ('title','description','brand','model_or_markings','room_or_area')
    autocomplete_fields = ('owner','category')
    actions = [approve_items]
    inlines = [LostMatchInline, FoundMatchInline]

    def match_count(self, obj):
        return obj.lost_matches.count() + obj.found_matches.count()
    match_count.short_description = "Potential matches"

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'lost_item', 'found_item', 'score', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('lost_item__title', 'found_item__title')

    readonly_fields = ('explanation',)

    def explanation(self, obj):
        """Show why this lost/found pair matched."""
        return explain_match(obj.lost_item, obj.found_item)

    explanation.short_description = "Match criteria"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id','item','sender','receiver','sent_at','is_read')
    list_filter  = ('is_read',)
