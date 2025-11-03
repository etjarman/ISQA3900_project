from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from items import views as item_views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root':
    settings.MEDIA_ROOT}), #serve media files when deployed
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root':
    settings.STATIC_ROOT}), #serve static files when deployed

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', item_views.signup, name='signup'),
    path('accounts/profile/', RedirectView.as_view(pattern_name='items:home', permanent=False)),

    # App
    path('', include(('items.urls', 'items'), namespace='items')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
