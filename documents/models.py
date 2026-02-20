import secrets
from django.db import models


def _signed_path(instance, filename):
    p = instance.assignment.person
    safe = p.full_name.replace(" ", "_").lower()[:30]
    return f"signed_documents/{p.person_type}/{safe}/{filename}"


def _sig_path(instance, filename):
    return f"signatures/{instance.confirmation_id}/{filename}"


def _copy_path(instance, filename):
    return f"nda_copies/{instance.confirmation_id}/{filename}"


class SignedDocument(models.Model):
    assignment = models.OneToOneField(
        "assignments.NDAAssignment", on_delete=models.CASCADE,
        related_name="signed_document",
    )
    confirmation_id = models.CharField(max_length=50, unique=True, db_index=True)

    # Signer snapshot
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField()
    signer_company = models.CharField(max_length=255, blank=True, default="")
    signer_designation = models.CharField(max_length=255, blank=True, default="")
    signer_person_type = models.CharField(max_length=20)

    # NDA snapshot
    nda_name = models.CharField(max_length=255)
    nda_category = models.CharField(max_length=20)
    nda_version = models.CharField(max_length=20)
    nda_content_html = models.TextField()
    nda_content_plain = models.TextField()
    nda_content_hash = models.CharField(max_length=128)

    # Files
    nda_copy_docx = models.FileField(upload_to=_copy_path, blank=True, null=True)
    signature_image = models.ImageField(upload_to=_sig_path, blank=True, null=True)
    signature_type = models.CharField(max_length=20, default="drawn")
    signature_hash = models.CharField(max_length=128, blank=True, default="")
    signed_pdf = models.FileField(upload_to=_signed_path, blank=True, null=True)

    # Consent
    consent_text = models.TextField()
    consent_given = models.BooleanField(default=True)
    consent_timestamp = models.DateTimeField()

    # Metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default="")
    device_fingerprint = models.CharField(max_length=255, blank=True, default="")

    pdf_generated = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.confirmation_id} — {self.signer_name}"

    def save(self, *args, **kwargs):
        if not self.confirmation_id:
            yr = (
                self.consent_timestamp.year
                if self.consent_timestamp else 2026
            )
            self.confirmation_id = (
                f"NDA-{yr}-{secrets.token_hex(4).upper()}"
            )
        super().save(*args, **kwargs)
