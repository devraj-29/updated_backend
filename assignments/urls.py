from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"groups", views.GroupViewSet, basename="group")
router.register(r"", views.NDAAssignmentViewSet, basename="assignment")

urlpatterns = [path("", include(router.urls))]
