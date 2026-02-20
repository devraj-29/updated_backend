import hashlib
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class NDACategory(models.TextChoices):
    EMPLOYEE = "employee", "Employee"
    CLIENT = "client", "Client / Customer"
    PARTNER = "partner", "Partner"
    CONSULTANT = "consultant", "Consultant"
    FREELANCER = "freelancer", "Freelancer"
    VENDOR = "vendor", "Vendor"
    ADDITIONAL = "additional", "Additional"


class NDAStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


def nda_file_path(instance, filename):
    slug = instance.template.slug
    cat = instance.template.category
    ver = instance.version_number
    return f"nda_templates/{cat}/{slug}/v{ver}/{filename}"


class NDATemplate(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(
        max_length=20, choices=NDACategory.choices, db_index=True
    )
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=NDAStatus.choices,
        default=NDAStatus.DRAFT, db_index=True,
    )
    is_mandatory = models.BooleanField(default=True)
    current_version = models.OneToOneField(
        "NDAVersion", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    survival_years = models.IntegerField(default=5)
    requires_witness = models.BooleanField(default=False)
    auto_remind_days = models.IntegerField(default=3)
    link_expiry_hours = models.IntegerField(default=72)
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="created_ndas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:240]
            slug = base
            counter = 1
            while NDATemplate.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class NDAVersion(models.Model):
    template = models.ForeignKey(
        NDATemplate, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.CharField(max_length=20)
    changelog = models.TextField(blank=True, default="")
    content_html = models.TextField(blank=True, default="")
    content_plain = models.TextField(blank=True, default="")
    docx_file = models.FileField(upload_to=nda_file_path, blank=True, null=True)
    content_hash = models.CharField(max_length=128, blank=True, default="")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["template", "version_number"]

    def __str__(self):
        return f"{self.template.name} v{self.version_number}"

    def compute_hash(self):
        return hashlib.sha256(self.content_plain.encode()).hexdigest()
