from django.db import models
from django.conf import settings


class PersonType(models.TextChoices):
    EMPLOYEE = "employee", "Employee"
    CUSTOMER = "customer", "Customer"
    VENDOR = "vendor", "Vendor"
    FREELANCER = "freelancer", "Freelancer"
    CONSULTANT = "consultant", "Consultant"


class Person(models.Model):
    person_type = models.CharField(
        max_length=20, choices=PersonType.choices, db_index=True
    )
    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    designation = models.CharField(max_length=100, blank=True, default="")

    # Company (non-employees)
    company_name = models.CharField(max_length=255, blank=True, default="")
    company_address = models.TextField(blank=True, default="")
    company_gst = models.CharField(max_length=30, blank=True, default="")
    company_pan = models.CharField(max_length=20, blank=True, default="")

    # Employee-specific
    employee_id = models.CharField(max_length=50, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_exit = models.DateField(null=True, blank=True)
    reporting_manager = models.CharField(max_length=255, blank=True, default="")

    # ID verification
    id_type = models.CharField(max_length=50, blank=True, default="")
    id_number = models.CharField(max_length=100, blank=True, default="")

    # Contract (freelancers/consultants/vendors)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    contract_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="created_people",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "People"
        unique_together = ["email", "person_type"]

    def __str__(self):
        return f"{self.full_name} ({self.get_person_type_display()})"
