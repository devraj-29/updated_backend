from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"signed", views.SignedDocumentViewSet, basename="signed-doc")

urlpatterns = [
    path("portal/<str:token>/", views.portal_get_nda),
    path("portal/<str:token>/read/", views.portal_mark_read),
    path("portal/<str:token>/sign/", views.portal_sign),
    path("portal/<str:token>/decline/", views.portal_decline),
    path("", include(router.urls)),
]
