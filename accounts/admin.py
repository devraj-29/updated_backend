from django.contrib import admin
from accounts.models import User, AuditLog
from ndas.models import NDATemplate, NDAVersion
from people.models import Person
from assignments.models import NDAAssignment, NDAAssignmentGroup
from documents.models import SignedDocument


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "role", "department", "is_active", "last_login"]
    list_filter = ["role", "is_active"]
    search_fields = ["email", "full_name"]
    ordering = ["-created_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "description", "ip_address", "created_at"]
    list_filter = ["action"]
    readonly_fields = [
        "user", "action", "target_type", "target_id",
        "description", "metadata", "ip_address", "user_agent", "created_at",
    ]
    ordering = ["-created_at"]


@admin.register(NDATemplate)
class NDATemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "status", "is_mandatory", "created_at"]
    list_filter = ["category", "status"]
    search_fields = ["name"]


@admin.register(NDAVersion)
class NDAVersionAdmin(admin.ModelAdmin):
    list_display = ["template", "version_number", "is_active", "created_at"]
    list_filter = ["is_active"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["full_name", "person_type", "email", "company_name", "is_active"]
    list_filter = ["person_type", "is_active"]
    search_fields = ["full_name", "email"]


@admin.register(NDAAssignment)
class NDAAssignmentAdmin(admin.ModelAdmin):
    list_display = ["person", "nda_template", "status", "assigned_at", "signed_at"]
    list_filter = ["status"]
    search_fields = ["person__full_name", "nda_template__name"]


@admin.register(NDAAssignmentGroup)
class NDAAssignmentGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "total_assignments", "total_signed", "total_pending", "created_at"]


@admin.register(SignedDocument)
class SignedDocumentAdmin(admin.ModelAdmin):
    list_display = ["confirmation_id", "signer_name", "nda_name", "nda_version", "consent_timestamp"]
    readonly_fields = ["confirmation_id", "nda_content_hash", "signature_hash"]
    search_fields = ["confirmation_id", "signer_name"]
