from django.contrib import admin
from .models import Category, Item, Match, Message

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id','title','status','category','owner','building','date_lost_or_found','approved')
    list_filter  = ('status','category','approved','building')
    search_fields = ('title','description','brand','model_or_markings','room_or_area')
    autocomplete_fields = ('owner','category')

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id','lost_item','found_item','score','status','created_at')
    list_filter  = ('status',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id','item','sender','receiver','sent_at','is_read')
    list_filter  = ('is_read',)