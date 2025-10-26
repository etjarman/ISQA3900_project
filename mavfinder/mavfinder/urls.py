from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from items import views as item_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),   # login, logout, password_* views
    path('accounts/signup/', item_views.signup, name='signup'),

    # App
    path('', include(('items.urls','items'), namespace='items')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
