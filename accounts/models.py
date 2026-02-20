import hashlib
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    LEGAL = "legal", "Legal"
    HR = "hr", "HR"
    MANAGER = "manager", "Manager"
    EMPLOYEE = "employee", "Employee"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", UserRole.SUPER_ADMIN)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    designation = models.CharField(max_length=100, blank=True, default="")
    employee_id = models.CharField(max_length=50, blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.EMPLOYEE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def role_level(self):
        levels = {"super_admin": 5, "legal": 4, "hr": 3, "manager": 2, "employee": 1}
        return levels.get(self.role, 0)

    @property
    def can_manage_ndas(self):
        return self.role in ("super_admin", "legal", "hr")

    @property
    def can_assign_ndas(self):
        return self.role in ("super_admin", "legal", "hr", "manager")

    @property
    def can_manage_people(self):
        return self.role in ("super_admin", "hr", "manager")

    @property
    def can_manage_users(self):
        return self.role in ("super_admin", "hr")


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("user_created", "User Created"),
        ("user_updated", "User Updated"),
        ("nda_created", "NDA Created"),
        ("nda_updated", "NDA Updated"),
        ("nda_version_created", "Version Created"),
        ("nda_activated", "NDA Activated"),
        ("nda_archived", "NDA Archived"),
        ("nda_deleted", "NDA Deleted"),
        ("person_created", "Person Created"),
        ("person_updated", "Person Updated"),
        ("nda_assigned", "NDA Assigned"),
        ("nda_group_assigned", "Group Assigned"),
        ("nda_signed", "NDA Signed"),
        ("nda_declined", "NDA Declined"),
        ("nda_revoked", "NDA Revoked"),
        ("nda_reminded", "Reminder Sent"),
        ("doc_downloaded", "Document Downloaded"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    target_type = models.CharField(max_length=50, blank=True, default="")
    target_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.action} @ {self.created_at}"
