from rest_framework import serializers
from .models import Person


class PersonListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source="get_person_type_display", read_only=True
    )
    total_assigned = serializers.IntegerField(read_only=True, default=0)
    total_signed = serializers.IntegerField(read_only=True, default=0)
    total_pending = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Person
        fields = [
            "id", "person_type", "type_display", "full_name", "email",
            "phone", "designation", "company_name", "employee_id",
            "department", "is_active", "tags",
            "contract_start", "contract_end",
            "total_assigned", "total_signed", "total_pending",
            "created_at", "updated_at",
        ]


class PersonDetailSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source="get_person_type_display", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )

    class Meta:
        model = Person
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PersonCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "person_type", "full_name", "email", "phone", "designation",
            "company_name", "company_address", "company_gst", "company_pan",
            "employee_id", "department", "date_of_joining", "reporting_manager",
            "id_type", "id_number",
            "contract_start", "contract_end", "contract_value",
            "notes", "tags", "is_active",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
