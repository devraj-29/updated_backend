from rest_framework import serializers
from .models import NDAAssignment, NDAAssignmentGroup


class NDAAssignmentSerializer(serializers.ModelSerializer):
    nda_name = serializers.CharField(source="nda_template.name", read_only=True)
    nda_category = serializers.CharField(source="nda_template.category", read_only=True)
    version_number = serializers.CharField(
        source="nda_version.version_number", read_only=True
    )
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_email = serializers.CharField(source="person.email", read_only=True)
    person_type = serializers.CharField(source="person.person_type", read_only=True)
    person_company = serializers.CharField(
        source="person.company_name", read_only=True, default=""
    )
    assigned_by_name = serializers.CharField(
        source="assigned_by.full_name", read_only=True, default=""
    )
    group_name = serializers.CharField(
        source="group.name", read_only=True, default=None
    )
    signing_url = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    has_document = serializers.SerializerMethodField()

    class Meta:
        model = NDAAssignment
        fields = [
            "id", "nda_template", "nda_name", "nda_category",
            "nda_version", "version_number",
            "person", "person_name", "person_email",
            "person_type", "person_company",
            "group", "group_name", "token", "signing_url",
            "status", "is_expired",
            "assigned_at", "sent_at", "viewed_at", "read_at",
            "signed_at", "declined_at", "expires_at",
            "assigned_by", "assigned_by_name",
            "message", "reminder_count", "last_reminder_at",
            "signer_ip", "decline_reason", "has_document",
        ]
        read_only_fields = ["id", "token", "status", "assigned_at"]

    def get_has_document(self, obj):
        return hasattr(obj, "signed_document")


class SingleAssignSerializer(serializers.Serializer):
    nda_template_id = serializers.IntegerField()
    person_id = serializers.IntegerField()
    message = serializers.CharField(required=False, default="")
    send_immediately = serializers.BooleanField(default=True)


class GroupAssignSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="")
    nda_template_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    person_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    message = serializers.CharField(required=False, default="")
    link_expiry_hours = serializers.IntegerField(default=72)
    send_immediately = serializers.BooleanField(default=True)


class GroupSerializer(serializers.ModelSerializer):
    nda_names = serializers.SerializerMethodField()
    people_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )

    class Meta:
        model = NDAAssignmentGroup
        fields = [
            "id", "name", "description", "nda_names", "people_count",
            "total_assignments", "total_signed", "total_pending",
            "message", "created_by", "created_by_name", "created_at",
        ]

    def get_nda_names(self, obj):
        return list(obj.nda_templates.values_list("name", flat=True))

    def get_people_count(self, obj):
        return obj.people.count()
