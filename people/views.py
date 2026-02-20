from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManagePeople
from accounts.views import log_action

from .models import Person
from .serializers import (
    PersonCreateSerializer,
    PersonDetailSerializer,
    PersonListSerializer,
)


class PersonViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManagePeople]
    filterset_fields = ["person_type", "is_active", "department", "company_name"]
    search_fields = ["full_name", "email", "company_name", "employee_id", "phone"]
    ordering_fields = ["full_name", "created_at", "person_type"]

    def get_queryset(self):
        return (
            Person.objects
            .select_related("created_by")
            .annotate(
                total_assigned=Count("nda_assignments"),
                total_signed=Count(
                    "nda_assignments",
                    filter=Q(nda_assignments__status="signed"),
                ),
                total_pending=Count(
                    "nda_assignments",
                    filter=Q(nda_assignments__status__in=[
                        "sent", "viewed", "read"
                    ]),
                ),
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PersonListSerializer
        if self.action == "retrieve":
            return PersonDetailSerializer
        return PersonCreateSerializer

    def perform_create(self, serializer):
        p = serializer.save()
        log_action(
            self.request.user, "person_created", "Person", p.id,
            f"Created {p.get_person_type_display()}: {p.full_name}",
            self.request,
        )

    def perform_update(self, serializer):
        p = serializer.save()
        log_action(
            self.request.user, "person_updated", "Person", p.id,
            f"Updated: {p.full_name}", self.request,
        )

    @action(detail=False, methods=["get"], url_path="by-type")
    def by_type(self, request):
        stats = list(
            Person.objects.values("person_type")
            .annotate(count=Count("id"))
            .order_by("person_type")
        )
        return Response(stats)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        items = request.data.get("people", [])
        if not items:
            return Response({"error": "Provide 'people' array."}, status=400)
        created = []
        errors = []
        for idx, item in enumerate(items):
            s = PersonCreateSerializer(data=item, context={"request": request})
            if s.is_valid():
                p = s.save()
                created.append(p.id)
            else:
                errors.append({"index": idx, "errors": s.errors})
        return Response(
            {"created": len(created), "ids": created, "errors": errors},
            status=201,
        )
