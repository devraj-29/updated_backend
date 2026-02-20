from rest_framework import serializers
from .models import User, AuditLog


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    can_manage_ndas = serializers.BooleanField(read_only=True)
    can_assign_ndas = serializers.BooleanField(read_only=True)
    can_manage_people = serializers.BooleanField(read_only=True)
    can_manage_users = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "department",
            "designation", "employee_id", "role", "role_display",
            "is_active", "avatar", "last_login", "last_login_ip",
            "can_manage_ndas", "can_assign_ndas",
            "can_manage_people", "can_manage_users",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "last_login", "last_login_ip",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            "email", "full_name", "password", "phone",
            "department", "designation", "employee_id", "role",
        ]

    def create(self, validated_data):
        pw = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(pw)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name", "phone", "department", "designation",
            "employee_id", "role", "is_active",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source="user.full_name", read_only=True, default="System"
    )
    user_email = serializers.CharField(
        source="user.email", read_only=True, default=""
    )

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_name", "user_email", "action",
            "target_type", "target_id", "description", "metadata",
            "ip_address", "user_agent", "created_at",
        ]
