from django.urls import path
from . import views
app_name = 'items'

urlpatterns = [
  path('', views.home, name='home'),
  path('items/', views.item_list, name='item_list'),
  path('items/create/', views.item_create, name='item_create'),
  path('items/<int:pk>/', views.item_detail, name='item_detail'),
  path('items/<int:pk>/edit/', views.item_update, name='item_update'),
  path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
  path('account/', views.my_account, name='account'),
  path('admin-review/matches/', views.match_review, name='match_review'),
]
