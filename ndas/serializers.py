import hashlib
from rest_framework import serializers
from .models import NDATemplate, NDAVersion


class NDAVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    docx_url = serializers.SerializerMethodField()

    class Meta:
        model = NDAVersion
        fields = [
            "id", "template", "version_number", "changelog",
            "content_html", "content_plain", "docx_file", "docx_url",
            "content_hash", "is_active", "effective_date",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["id", "content_hash", "created_at"]

    def get_docx_url(self, obj):
        if obj.docx_file:
            req = self.context.get("request")
            if req:
                return req.build_absolute_uri(obj.docx_file.url)
            return obj.docx_file.url
        return None


class NDAVersionCreateSerializer(serializers.Serializer):
    version_number = serializers.CharField(max_length=20)
    changelog = serializers.CharField(required=False, default="")
    content_html = serializers.CharField(required=False, default="")
    content_plain = serializers.CharField(required=False, default="")
    docx_file = serializers.FileField(required=False)
    effective_date = serializers.DateField(required=False, allow_null=True)


class NDATemplateListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    current_version_number = serializers.CharField(
        source="current_version.version_number", read_only=True, default=None
    )
    current_version_id = serializers.IntegerField(
        source="current_version.id", read_only=True, default=None
    )
    version_count = serializers.IntegerField(read_only=True, default=0)
    total_assigned = serializers.IntegerField(read_only=True, default=0)
    total_signed = serializers.IntegerField(read_only=True, default=0)
    total_pending = serializers.IntegerField(read_only=True, default=0)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    has_docx = serializers.SerializerMethodField()

    class Meta:
        model = NDATemplate
        fields = [
            "id", "name", "slug", "category", "category_display",
            "description", "status", "status_display", "is_mandatory",
            "survival_years", "tags",
            "current_version", "current_version_number", "current_version_id",
            "version_count", "total_assigned", "total_signed", "total_pending",
            "has_docx", "requires_witness", "auto_remind_days", "link_expiry_hours",
            "created_by", "created_by_name", "created_at", "updated_at",
        ]

    def get_has_docx(self, obj):
        return bool(obj.current_version and obj.current_version.docx_file)


class NDATemplateDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    versions = NDAVersionSerializer(many=True, read_only=True)
    current_version_data = NDAVersionSerializer(
        source="current_version", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )

    class Meta:
        model = NDATemplate
        fields = [
            "id", "name", "slug", "category", "category_display",
            "description", "status", "is_mandatory", "survival_years",
            "requires_witness", "auto_remind_days", "link_expiry_hours",
            "tags", "current_version", "current_version_data",
            "versions", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]


class NDATemplateCreateSerializer(serializers.ModelSerializer):
    version_number = serializers.CharField(default="1.0", write_only=True)
    content_html = serializers.CharField(write_only=True, required=False, default="")
    content_plain = serializers.CharField(write_only=True, required=False, default="")
    docx_file = serializers.FileField(required=False, write_only=True)
    changelog = serializers.CharField(
        default="Initial version", write_only=True, required=False
    )

    class Meta:
        model = NDATemplate
        fields = [
            "name", "category", "description", "is_mandatory",
            "survival_years", "requires_witness", "auto_remind_days",
            "link_expiry_hours", "tags",
            "version_number", "content_html", "content_plain",
            "docx_file", "changelog",
        ]

    def create(self, validated_data):
        vn = validated_data.pop("version_number", "1.0")
        html = validated_data.pop("content_html", "")
        plain = validated_data.pop("content_plain", "")
        docx = validated_data.pop("docx_file", None)
        cl = validated_data.pop("changelog", "Initial version")

        user = self.context["request"].user
        validated_data["created_by"] = user

        tpl = NDATemplate.objects.create(**validated_data)

        ch = hashlib.sha256(plain.encode()).hexdigest() if plain else ""
        ver = NDAVersion.objects.create(
            template=tpl, version_number=vn, changelog=cl,
            content_html=html, content_plain=plain,
            docx_file=docx, content_hash=ch, created_by=user,
        )
        tpl.current_version = ver
        tpl.save(update_fields=["current_version"])
        return tpl


class NDATemplateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NDATemplate
        fields = [
            "name", "category", "description", "status",
            "is_mandatory", "survival_years", "requires_witness",
            "auto_remind_days", "link_expiry_hours", "tags",
        ]
