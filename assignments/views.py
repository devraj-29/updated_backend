from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanAssignNDAs
from accounts.views import log_action
from ndas.models import NDATemplate
from people.models import Person

from .emails import send_nda_assigned, send_nda_reminder
from .models import NDAAssignment, NDAAssignmentGroup
from .serializers import (
    GroupAssignSerializer,
    GroupSerializer,
    NDAAssignmentSerializer,
    SingleAssignSerializer,
)


class NDAAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = NDAAssignmentSerializer
    permission_classes = [CanAssignNDAs]
    filterset_fields = [
        "status", "nda_template__category", "person__person_type", "group",
    ]
    search_fields = ["person__full_name", "person__email", "nda_template__name"]
    ordering_fields = ["assigned_at", "signed_at", "status"]

    def get_queryset(self):
        return NDAAssignment.objects.select_related(
            "nda_template", "nda_version", "person", "assigned_by", "group",
        )

    @action(detail=False, methods=["post"], url_path="assign-single")
    def assign_single(self, request):
        s = SingleAssignSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        tpl = get_object_or_404(NDATemplate, id=d["nda_template_id"])
        person = get_object_or_404(Person, id=d["person_id"])

        if not tpl.current_version:
            return Response({"error": "NDA has no version."}, status=400)
        if tpl.status != "active":
            return Response({"error": "NDA is not active."}, status=400)

        dup = NDAAssignment.objects.filter(
            nda_template=tpl, person=person,
            nda_version=tpl.current_version,
            status__in=["draft", "sent", "viewed", "read"],
        ).exists()
        if dup:
            return Response(
                {"error": "Active assignment already exists."}, status=400
            )

        a = NDAAssignment.objects.create(
            nda_template=tpl,
            nda_version=tpl.current_version,
            person=person,
            assigned_by=request.user,
            message=d.get("message", ""),
        )
        if d.get("send_immediately", True):
            a.mark_sent()
            send_nda_assigned(a)

        log_action(
            request.user, "nda_assigned", "NDAAssignment", a.id,
            f"Assigned '{tpl.name}' to {person.full_name}", request,
            {"nda_id": tpl.id, "person_id": person.id},
        )
        return Response(NDAAssignmentSerializer(a).data, status=201)

    @action(detail=False, methods=["post"], url_path="assign-group")
    def assign_group(self, request):
        s = GroupAssignSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        templates = list(NDATemplate.objects.filter(id__in=d["nda_template_ids"]))
        people = list(Person.objects.filter(id__in=d["person_ids"]))

        if len(templates) != len(d["nda_template_ids"]):
            return Response({"error": "Some NDAs not found."}, status=400)
        if len(people) != len(d["person_ids"]):
            return Response({"error": "Some people not found."}, status=400)

        for t in templates:
            if not t.current_version:
                return Response({"error": f"'{t.name}' has no version."}, status=400)

        grp = NDAAssignmentGroup.objects.create(
            name=d["name"],
            description=d.get("description", ""),
            message=d.get("message", ""),
            link_expiry_hours=d.get("link_expiry_hours", 72),
            created_by=request.user,
        )
        grp.nda_templates.set(templates)
        grp.people.set(people)

        created, skipped = [], []
        for tpl in templates:
            for person in people:
                dup = NDAAssignment.objects.filter(
                    nda_template=tpl, person=person,
                    nda_version=tpl.current_version,
                    status__in=["draft", "sent", "viewed", "read", "signed"],
                ).exists()
                if dup:
                    skipped.append(f"{person.full_name} × {tpl.name}")
                    continue
                a = NDAAssignment.objects.create(
                    nda_template=tpl,
                    nda_version=tpl.current_version,
                    person=person,
                    group=grp,
                    assigned_by=request.user,
                    message=d.get("message", ""),
                )
                if d.get("send_immediately", True):
                    a.mark_sent(hours=d.get("link_expiry_hours", 72))
                    send_nda_assigned(a)
                created.append(a)

        grp.refresh_stats()
        log_action(
            request.user, "nda_group_assigned",
            "NDAAssignmentGroup", grp.id,
            f"Group '{grp.name}': {len(created)} assigned, {len(skipped)} skipped",
            request,
        )

        return Response({
            "group_id": grp.id,
            "group_name": grp.name,
            "created": len(created),
            "skipped": len(skipped),
            "skipped_details": skipped,
            "assignments": NDAAssignmentSerializer(created, many=True).data,
        }, status=201)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        a = self.get_object()
        if a.status == "signed":
            return Response({"error": "Already signed."}, status=400)
        a.mark_sent()
        send_nda_assigned(a)
        return Response({"message": "Sent.", "signing_url": a.signing_url})

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        a = self.get_object()
        if a.status not in ("sent", "viewed", "read"):
            return Response({"error": "Cannot send reminder."}, status=400)
        a.reminder_count += 1
        a.last_reminder_at = timezone.now()
        a.save(update_fields=["reminder_count", "last_reminder_at"])
        send_nda_reminder(a)
        log_action(
            request.user, "nda_reminded", "NDAAssignment", a.id,
            f"Reminder #{a.reminder_count} to {a.person.full_name}",
            request,
        )
        return Response({"message": f"Reminder #{a.reminder_count} sent."})

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        a = self.get_object()
        if a.status == "signed":
            return Response({"error": "Cannot revoke signed NDA."}, status=400)
        a.mark_revoked()
        log_action(
            request.user, "nda_revoked", "NDAAssignment", a.id,
            f"Revoked for {a.person.full_name}", request,
        )
        return Response({"message": "Revoked."})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            "total": qs.count(),
            "signed": qs.filter(status="signed").count(),
            "pending": qs.filter(status__in=["sent", "viewed", "read"]).count(),
            "expired": qs.filter(status="expired").count(),
            "declined": qs.filter(status="declined").count(),
            "revoked": qs.filter(status="revoked").count(),
        })


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        NDAAssignmentGroup.objects
        .select_related("created_by")
        .prefetch_related("nda_templates", "people")
    )
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        grp = self.get_object()
        qs = grp.assignments.select_related("nda_template", "person", "nda_version")
        return Response(NDAAssignmentSerializer(qs, many=True).data)
