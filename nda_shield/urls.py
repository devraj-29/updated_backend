from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("api/auth/", include("accounts.urls")),
    path("api/ndas/", include("ndas.urls")),
    path("api/people/", include("people.urls")),
    path("api/assignments/", include("assignments.urls")),
    path("api/documents/", include("documents.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler400 = "nda_shield.errors.api_400"
handler403 = "nda_shield.errors.api_403"
handler404 = "nda_shield.errors.api_404"
handler500 = "nda_shield.errors.api_500"
