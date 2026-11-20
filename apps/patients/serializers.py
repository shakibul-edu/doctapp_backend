from rest_framework import serializers

from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            "id", "email", "date_of_birth", "gender", "address",
            "profile_picture", "emergency_contact_name",
            "emergency_contact_phone", "created_at", "updated_at",
        )
        read_only_fields = ("id", "email", "created_at", "updated_at")
