from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"audit-logs", views.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("login/", views.login_view),
    path("logout/", views.logout_view),
    path("refresh/", views.refresh_view),
    path("me/", views.me_view),
    path("dashboard/", views.dashboard_view),
    path("encryption-key/", views.encryption_key_view),
    path("", include(router.urls)),
]
