from rest_framework import serializers

from apps.accounts.models import User
from .models import DoctorAssistant, DoctorProfile


class DoctorPublicSerializer(serializers.ModelSerializer):
    hospital_ids = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = (
            "id", "professional_name", "profile_picture", "bio", "specialty",
            "qualifications", "experience_years", "consultation_fee",
            "languages", "hospital_ids", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_hospital_ids(self, obj):
        return list(
            obj.chambers.filter(active=True, hospital__isnull=False)
            .values_list("hospital_id", flat=True)
            .distinct()
        )


class DoctorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = (
            "professional_name", "profile_picture", "bio", "specialty",
            "qualifications", "experience_years", "medical_registration_number",
            "consultation_fee", "languages",
        )


class DoctorAssistantSerializer(serializers.ModelSerializer):
    assistant_id = serializers.UUIDField(source="assistant.id", read_only=True)
    assistant_email = serializers.EmailField(source="assistant.email", read_only=True)
    assistant_name = serializers.CharField(source="assistant.full_name", read_only=True)

    class Meta:
        model = DoctorAssistant
        fields = (
            "id", "assistant_id", "assistant_email", "assistant_name", "active",
            "can_view_patient_profiles", "can_manage_chambers",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "assistant_id", "assistant_email", "assistant_name",
            "created_at", "updated_at",
        )


class DoctorAssistantCreateSerializer(serializers.Serializer):
    assistant_id = serializers.UUIDField()
    active = serializers.BooleanField(default=True)
    can_view_patient_profiles = serializers.BooleanField(default=False)
    can_manage_chambers = serializers.BooleanField(default=False)

    def validate_assistant_id(self, value):
        try:
            assistant = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Assistant account does not exist.")
        if assistant.role != User.Role.ASSISTANT:
            raise serializers.ValidationError("The selected user is not an assistant.")
        if not assistant.is_active or assistant.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError("The assistant account is not active.")
        return assistant
