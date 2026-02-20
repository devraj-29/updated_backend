import hashlib

from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import CanManageNDAs
from accounts.views import log_action

from .models import NDACategory, NDATemplate, NDAVersion
from .serializers import (
    NDATemplateCreateSerializer,
    NDATemplateDetailSerializer,
    NDATemplateListSerializer,
    NDATemplateUpdateSerializer,
    NDAVersionCreateSerializer,
    NDAVersionSerializer,
)


class NDATemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageNDAs]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["category", "status", "is_mandatory"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "category", "created_at", "updated_at"]

    def get_queryset(self):
        return (
            NDATemplate.objects
            .select_related("current_version", "created_by")
            .annotate(
                version_count=Count("versions"),
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
            return NDATemplateListSerializer
        if self.action == "retrieve":
            return NDATemplateDetailSerializer
        if self.action == "create":
            return NDATemplateCreateSerializer
        if self.action in ("update", "partial_update"):
            return NDATemplateUpdateSerializer
        return NDATemplateDetailSerializer

    def perform_create(self, serializer):
        tpl = serializer.save()
        log_action(
            self.request.user, "nda_created", "NDATemplate", tpl.id,
            f"Created NDA template: {tpl.name}", self.request,
        )

    def perform_update(self, serializer):
        tpl = serializer.save()
        log_action(
            self.request.user, "nda_updated", "NDATemplate", tpl.id,
            f"Updated NDA: {tpl.name}", self.request,
        )

    def perform_destroy(self, instance):
        """Soft-delete: archive instead of deleting if assignments exist."""
        has_assignments = instance.nda_assignments.exists()
        name = instance.name
        if has_assignments:
            instance.status = "archived"
            instance.save(update_fields=["status"])
            log_action(
                self.request.user, "nda_archived", "NDATemplate", instance.id,
                f"Soft-deleted (archived, has assignments): {name}", self.request,
            )
        else:
            pk = instance.id
            instance.delete()
            log_action(
                self.request.user, "nda_deleted", "NDATemplate", pk,
                f"Permanently deleted: {name}", self.request,
            )

    @action(detail=True, methods=["post"], url_path="new-version")
    def create_version(self, request, pk=None):
        tpl = self.get_object()
        s = NDAVersionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        ch = ""
        if d.get("content_plain"):
            ch = hashlib.sha256(d["content_plain"].encode()).hexdigest()

        # Deactivate all existing versions
        tpl.versions.update(is_active=False)

        ver = NDAVersion.objects.create(
            template=tpl,
            version_number=d["version_number"],
            changelog=d.get("changelog", ""),
            content_html=d.get("content_html", ""),
            content_plain=d.get("content_plain", ""),
            docx_file=d.get("docx_file"),
            effective_date=d.get("effective_date"),
            content_hash=ch,
            created_by=request.user,
        )
        tpl.current_version = ver
        tpl.save(update_fields=["current_version", "updated_at"])

        log_action(
            request.user, "nda_version_created", "NDATemplate", tpl.id,
            f"Created v{ver.version_number} for {tpl.name}", request,
        )
        return Response(
            NDAVersionSerializer(ver, context={"request": request}).data,
            status=201,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        tpl = self.get_object()
        if not tpl.current_version:
            return Response({"error": "No version exists."}, status=400)
        tpl.status = "active"
        tpl.save(update_fields=["status"])
        log_action(
            request.user, "nda_activated", "NDATemplate", tpl.id,
            f"Activated: {tpl.name}", request,
        )
        return Response({"message": f"'{tpl.name}' is now active."})

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        tpl = self.get_object()
        tpl.status = "archived"
        tpl.save(update_fields=["status"])
        log_action(
            request.user, "nda_archived", "NDATemplate", tpl.id,
            f"Archived: {tpl.name}", request,
        )
        return Response({"message": f"'{tpl.name}' archived."})

    @action(detail=True, methods=["get"], url_path="versions")
    def version_list(self, request, pk=None):
        tpl = self.get_object()
        vs = tpl.versions.all().order_by("-created_at")
        return Response(
            NDAVersionSerializer(vs, many=True, context={"request": request}).data
        )

    @action(detail=False, methods=["get"])
    def categories(self, request):
        out = []
        for c in NDACategory:
            cnt = NDATemplate.objects.filter(category=c.value).count()
            out.append({"value": c.value, "label": c.label, "count": cnt})
        return Response(out)
