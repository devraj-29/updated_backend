from datetime import timedelta

from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.utils import timezone
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauth2_provider.settings import oauth2_settings
from oauthlib.common import generate_token
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User, AuditLog
from .permissions import CanManageUsers
from .serializers import (
    AuditLogSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


# ── Helpers ──────────────────────────────────────────────

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


def log_action(user, action, target_type="", target_id=None,
               desc="", request=None, meta=None):
    AuditLog.objects.create(
        user=user if user and hasattr(user, "pk") else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=desc,
        metadata=meta or {},
        ip_address=get_client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:500]
                    if request else ""),
    )


def _get_app(user):
    app, _ = Application.objects.get_or_create(
        name="NDA Shield",
        defaults={
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_PASSWORD,
            "user": user,
        },
    )
    return app


def _issue_tokens(user, app):
    """Delete old tokens for this user+app, issue fresh pair."""
    AccessToken.objects.filter(user=user, application=app).delete()
    RefreshToken.objects.filter(user=user, application=app).delete()
    exp = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    at = AccessToken.objects.create(
        user=user, application=app,
        token=generate_token(), expires=exp, scope="read write",
    )
    rt = RefreshToken.objects.create(
        user=user, application=app,
        token=generate_token(), access_token=at,
    )
    return at, rt


# ── Auth Endpoints ───────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")
    if not email or not password:
        return Response(
            {"error": "Email and password required."}, status=400
        )

    user = authenticate(request, email=email, password=password)
    if not user:
        return Response({"error": "Invalid credentials."}, status=401)
    if not user.is_active:
        return Response({"error": "Account disabled."}, status=403)

    app = _get_app(user)
    at, rt = _issue_tokens(user, app)

    user.last_login = timezone.now()
    user.last_login_ip = get_client_ip(request)
    user.save(update_fields=["last_login", "last_login_ip"])
    log_action(user, "login", request=request,
               desc=f"{user.full_name} logged in")

    return Response({
        "access_token": at.token,
        "refresh_token": rt.token,
        "token_type": "Bearer",
        "expires_in": oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        "user": UserSerializer(user).data,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    token = request.data.get("refresh_token", "")
    if not token:
        return Response({"error": "refresh_token required."}, status=400)
    try:
        rt = RefreshToken.objects.select_related(
            "user", "application"
        ).get(token=token)
    except RefreshToken.DoesNotExist:
        return Response({"error": "Invalid refresh token."}, status=401)

    if rt.revoked:
        return Response({"error": "Token revoked."}, status=401)

    # Delete old access token
    if rt.access_token:
        rt.access_token.delete()

    exp = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    new_at = AccessToken.objects.create(
        user=rt.user, application=rt.application,
        token=generate_token(), expires=exp, scope="read write",
    )
    rt.access_token = new_at
    rt.token = generate_token()
    rt.save()

    return Response({
        "access_token": new_at.token,
        "refresh_token": rt.token,
        "token_type": "Bearer",
        "expires_in": oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    if request.auth:
        RefreshToken.objects.filter(access_token=request.auth).delete()
        request.auth.delete()
    log_action(request.user, "logout", request=request,
               desc=f"{request.user.full_name} logged out")
    return Response({"message": "Logged out."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def encryption_key_view(request):
    """Return the Fernet encryption key for client-side encryption."""
    from django.conf import settings as s
    return Response({
        "key": s.ENCRYPTION_KEY.decode() if isinstance(s.ENCRYPTION_KEY, bytes) else s.ENCRYPTION_KEY,
        "algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)",
        "usage": "Set header X-Encrypted: true and encrypt/decrypt body with this key.",
    })


# ── User Management ─────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    filterset_fields = ["role", "is_active", "department"]
    search_fields = ["email", "full_name", "employee_id"]
    ordering_fields = ["created_at", "full_name", "role"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [CanManageUsers()]

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(
            self.request.user, "user_created", "User", user.id,
            f"Created user {user.full_name} ({user.role})", self.request,
        )

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(
            self.request.user, "user_updated", "User", user.id,
            f"Updated user {user.full_name}", self.request,
        )


# ── Audit Log ────────────────────────────────────────────

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["action", "user", "target_type"]
    search_fields = ["description"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user").all()
        # Non-admins see only own logs
        if self.request.user.role not in ("super_admin", "legal"):
            qs = qs.filter(user=self.request.user)
        return qs


# ── Dashboard ────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    from ndas.models import NDATemplate
    from people.models import Person
    from assignments.models import NDAAssignment
    from documents.models import SignedDocument

    total_ndas = NDATemplate.objects.count()
    active_ndas = NDATemplate.objects.filter(status="active").count()
    total_people = Person.objects.count()
    total_assignments = NDAAssignment.objects.count()
    total_signed = NDAAssignment.objects.filter(status="signed").count()
    total_pending = NDAAssignment.objects.filter(
        status__in=["sent", "viewed", "read"]
    ).count()
    total_expired = NDAAssignment.objects.filter(status="expired").count()
    total_declined = NDAAssignment.objects.filter(status="declined").count()
    total_documents = SignedDocument.objects.count()
    total_users = User.objects.filter(is_active=True).count()

    rate = (
        round(total_signed / total_assignments * 100, 1)
        if total_assignments > 0 else 0
    )

    category_stats = list(
        NDATemplate.objects.values("category").annotate(
            count=Count("id"),
            assigned=Count("nda_assignments"),
            signed=Count(
                "nda_assignments",
                filter=Q(nda_assignments__status="signed"),
            ),
        ).order_by("category")
    )

    people_stats = list(
        Person.objects.values("person_type").annotate(
            count=Count("id")
        ).order_by("person_type")
    )

    recent_activity = AuditLogSerializer(
        AuditLog.objects.select_related("user")[:15], many=True
    ).data

    return Response({
        "total_ndas": total_ndas,
        "active_ndas": active_ndas,
        "total_people": total_people,
        "total_users": total_users,
        "total_assignments": total_assignments,
        "total_signed": total_signed,
        "total_pending": total_pending,
        "total_expired": total_expired,
        "total_declined": total_declined,
        "total_documents": total_documents,
        "signing_rate": rate,
        "category_stats": category_stats,
        "people_stats": people_stats,
        "recent_activity": recent_activity,
    })
