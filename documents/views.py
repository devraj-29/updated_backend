import base64
import hashlib

from django.conf import settings as django_settings
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.views import log_action
from assignments.emails import (
    send_nda_declined_notification,
    send_nda_signed_confirmation,
    send_nda_signed_notification_to_admin,
)
from assignments.models import NDAAssignment

from .models import SignedDocument
from .serializers import (
    SignedDocDetailSerializer,
    SignedDocListSerializer,
    SignRequestSerializer,
)


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


class SignedDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SignedDocument.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["signer_person_type", "nda_category"]
    search_fields = [
        "signer_name", "signer_email", "nda_name", "confirmation_id",
    ]
    ordering_fields = ["consent_timestamp", "nda_name"]

    def get_serializer_class(self):
        if self.action == "list":
            return SignedDocListSerializer
        return SignedDocDetailSerializer

    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request, pk=None):
        doc = self.get_object()
        if not doc.signed_pdf:
            return Response({"error": "PDF not available."}, status=404)
        log_action(
            request.user, "doc_downloaded", "SignedDocument", doc.id,
            f"Downloaded PDF: {doc.confirmation_id}", request,
        )
        return FileResponse(
            doc.signed_pdf.open(),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"{doc.confirmation_id}.pdf",
        )

    @action(detail=True, methods=["get"], url_path="download-docx")
    def download_docx(self, request, pk=None):
        doc = self.get_object()
        if not doc.nda_copy_docx:
            return Response({"error": "DOCX not available."}, status=404)
        return FileResponse(
            doc.nda_copy_docx.open(),
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
            as_attachment=True,
            filename=f"{doc.nda_name}_v{doc.nda_version}.docx",
        )

    @action(detail=False, methods=["get"], url_path="by-person/(?P<pid>[0-9]+)")
    def by_person(self, request, pid=None):
        docs = self.queryset.filter(assignment__person_id=pid)
        return Response(SignedDocListSerializer(docs, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="by-nda/(?P<nid>[0-9]+)")
    def by_nda(self, request, nid=None):
        docs = self.queryset.filter(assignment__nda_template_id=nid)
        return Response(SignedDocListSerializer(docs, many=True, context={"request": request}).data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SIGNING PORTAL — Token-based, NO AUTH, Enforced Read-First
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _validate_token(token):
    """Common token validation. Returns (assignment, error_response)."""
    a = get_object_or_404(NDAAssignment, token=token)

    if a.status == "signed":
        return None, Response({
            "error": "This NDA has already been signed. This link is no longer active.",
            "code": "ALREADY_SIGNED",
            "signed": True,
        }, status=410)

    if a.status == "revoked":
        return None, Response({
            "error": "This assignment has been revoked by the administrator.",
            "code": "REVOKED",
        }, status=410)

    if a.status == "declined":
        return None, Response({
            "error": "This NDA was declined. This link is no longer active.",
            "code": "DECLINED",
        }, status=410)

    if a.is_expired:
        a.status = "expired"
        a.save(update_fields=["status"])
        return None, Response({
            "error": "This signing link has expired. Please contact the sender for a new link.",
            "code": "EXPIRED",
        }, status=410)

    return a, None


@api_view(["GET"])
@permission_classes([AllowAny])
def portal_get_nda(request, token):
    """Step 1: View the NDA. Returns full NDA content."""
    a, err = _validate_token(token)
    if err:
        return err

    a.mark_viewed(ip=_ip(request), ua=request.META.get("HTTP_USER_AGENT", ""))

    return Response({
        "nda_name": a.nda_template.name,
        "nda_category": a.nda_template.category,
        "nda_version": a.nda_version.version_number,
        "content_html": a.nda_version.content_html,
        "content_plain": a.nda_version.content_plain,
        "signer_name": a.person.full_name,
        "signer_email": a.person.email,
        "signer_company": a.person.company_name,
        "requires_witness": a.nda_template.requires_witness,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "message": a.message,
        "company_name": django_settings.COMPANY_NAME,
        "assigned_by": a.assigned_by.full_name if a.assigned_by else "System",
        "status": a.status,
        "has_read": a.status in ("read",),
        "can_sign": a.status == "read",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def portal_mark_read(request, token):
    """Step 2: Mark NDA as fully read. REQUIRED before signing."""
    a, err = _validate_token(token)
    if err:
        return err

    if a.status not in ("sent", "viewed"):
        if a.status == "read":
            return Response({"status": "already_read", "can_sign": True})
        return Response({"error": "Cannot mark as read in current state."}, status=400)

    a.mark_read()
    return Response({
        "status": "read",
        "can_sign": True,
        "message": "NDA marked as read. You may now proceed to sign.",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def portal_sign(request, token):
    """Step 3: Sign the NDA. REQUIRES status='read' — must read first!"""
    a, err = _validate_token(token)
    if err:
        return err

    # ── ENFORCE READ-FIRST ──
    if a.status != "read":
        if a.status in ("sent", "viewed"):
            return Response({
                "error": "You must read the entire NDA before signing.",
                "code": "NOT_READ",
                "message": "Please scroll through the complete NDA document and mark it as read first.",
            }, status=403)
        return Response({"error": f"Cannot sign in '{a.status}' state."}, status=400)

    s = SignRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data

    ip = _ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")
    person = a.person
    ver = a.nda_version
    tpl = a.nda_template
    now = timezone.now()

    # Process signature
    sig_bytes = None
    if d.get("signature_image_base64"):
        raw = d["signature_image_base64"]
        if "," in raw:
            raw = raw.split(",", 1)[1]
        sig_bytes = base64.b64decode(raw)
    sig_hash = hashlib.sha256(sig_bytes).hexdigest() if sig_bytes else ""
    content_hash = hashlib.sha256(ver.content_plain.encode()).hexdigest()

    doc = SignedDocument(
        assignment=a,
        signer_name=person.full_name,
        signer_email=person.email,
        signer_company=person.company_name,
        signer_designation=person.designation,
        signer_person_type=person.person_type,
        nda_name=tpl.name,
        nda_category=tpl.category,
        nda_version=ver.version_number,
        nda_content_html=ver.content_html,
        nda_content_plain=ver.content_plain,
        nda_content_hash=content_hash,
        signature_type="drawn",
        signature_hash=sig_hash,
        consent_text=d["consent_text"],
        consent_given=True,
        consent_timestamp=now,
        ip_address=ip,
        user_agent=ua[:500],
    )

    if sig_bytes:
        doc.signature_image.save(
            f"sig_{now.strftime('%Y%m%d%H%M%S')}.png",
            ContentFile(sig_bytes), save=False,
        )

    if ver.docx_file:
        try:
            doc.nda_copy_docx.save(
                f"{tpl.slug}_v{ver.version_number}.docx",
                ContentFile(ver.docx_file.read()), save=False,
            )
        except Exception:
            pass

    doc.save()

    # ── Mark signed — KILLS THE LINK PERMANENTLY ──
    a.mark_signed(ip=ip, ua=ua)

    log_action(
        None, "nda_signed", "SignedDocument", doc.id,
        f"{person.full_name} signed '{tpl.name}' v{ver.version_number}",
        request,
        {"confirmation_id": doc.confirmation_id, "hash": content_hash},
    )

    # ── Send confirmation emails ──
    send_nda_signed_confirmation(a, doc)
    send_nda_signed_notification_to_admin(a, doc)

    return Response({
        "confirmation_id": doc.confirmation_id,
        "signed_at": now.isoformat(),
        "nda_name": tpl.name,
        "signer_name": person.full_name,
        "message": "NDA signed successfully. Confirmation email sent.",
        "link_status": "expired",
    }, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def portal_decline(request, token):
    """Decline NDA — kills the link."""
    a, err = _validate_token(token)
    if err:
        return err

    reason = request.data.get("reason", "")
    a.mark_declined(reason=reason)
    log_action(
        None, "nda_declined", "NDAAssignment", a.id,
        f"{a.person.full_name} declined '{a.nda_template.name}'",
        request,
    )
    send_nda_declined_notification(a)
    return Response({
        "status": "declined",
        "message": "NDA declined. The sender has been notified.",
        "link_status": "expired",
    })
