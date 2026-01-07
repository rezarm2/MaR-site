from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "date_joined", "role", "is_active"]

    def get_full_name(self, obj):
        return obj.get_full_name() or ""

    def get_role(self, obj):
        return "admin" if obj.is_staff else "user"
