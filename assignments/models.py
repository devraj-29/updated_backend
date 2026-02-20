import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class AssignmentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    VIEWED = "viewed", "Viewed"
    READ = "read", "Read"
    SIGNED = "signed", "Signed"
    DECLINED = "declined", "Declined"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


def _make_token():
    return secrets.token_urlsafe(48)


class NDAAssignmentGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    nda_templates = models.ManyToManyField(
        "ndas.NDATemplate", related_name="assignment_groups"
    )
    people = models.ManyToManyField(
        "people.Person", related_name="assignment_groups"
    )
    message = models.TextField(blank=True, default="")
    link_expiry_hours = models.IntegerField(default=72)
    total_assignments = models.IntegerField(default=0)
    total_signed = models.IntegerField(default=0)
    total_pending = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def refresh_stats(self):
        qs = self.assignments.all()
        self.total_assignments = qs.count()
        self.total_signed = qs.filter(status="signed").count()
        self.total_pending = qs.filter(
            status__in=["sent", "viewed", "read"]
        ).count()
        self.save(update_fields=[
            "total_assignments", "total_signed", "total_pending"
        ])


class NDAAssignment(models.Model):
    nda_template = models.ForeignKey(
        "ndas.NDATemplate", on_delete=models.CASCADE,
        related_name="nda_assignments",
    )
    nda_version = models.ForeignKey(
        "ndas.NDAVersion", on_delete=models.CASCADE,
        related_name="nda_assignments",
    )
    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE,
        related_name="nda_assignments",
    )
    group = models.ForeignKey(
        NDAAssignmentGroup, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assignments",
    )
    token = models.CharField(
        max_length=128, unique=True, db_index=True, default=_make_token
    )
    status = models.CharField(
        max_length=20, choices=AssignmentStatus.choices,
        default=AssignmentStatus.DRAFT, db_index=True,
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="assigned_ndas",
    )
    message = models.TextField(blank=True, default="")
    reminder_count = models.IntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)

    signer_ip = models.GenericIPAddressField(null=True, blank=True)
    signer_user_agent = models.TextField(blank=True, default="")
    decline_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.person.full_name} → {self.nda_template.name} ({self.status})"

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def signing_url(self):
        return f"{settings.FRONTEND_URL}/sign/{self.token}"

    def mark_sent(self, hours=None):
        self.status = "sent"
        self.sent_at = timezone.now()
        h = hours or self.nda_template.link_expiry_hours
        self.expires_at = timezone.now() + timedelta(hours=h)
        self.save()

    def mark_viewed(self, ip=None, ua=None):
        if self.status == "sent":
            self.status = "viewed"
            self.viewed_at = timezone.now()
            if ip:
                self.signer_ip = ip
            if ua:
                self.signer_user_agent = ua[:500]
            self.save()

    def mark_read(self):
        if self.status in ("sent", "viewed"):
            self.status = "read"
            self.read_at = timezone.now()
            self.save()

    def mark_signed(self, ip=None, ua=None):
        self.status = "signed"
        self.signed_at = timezone.now()
        if ip:
            self.signer_ip = ip
        if ua:
            self.signer_user_agent = ua[:500]
        self.save()
        if self.group:
            self.group.refresh_stats()

    def mark_declined(self, reason=""):
        self.status = "declined"
        self.declined_at = timezone.now()
        self.decline_reason = reason
        self.save()

    def mark_revoked(self):
        self.status = "revoked"
        self.save()
