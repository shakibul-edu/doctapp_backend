from rest_framework import serializers

from .models import Chamber, Hospital


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = (
            "id", "name", "description", "address", "contact_number",
            "latitude", "longitude", "active", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ChamberSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(source="doctor.id", read_only=True)
    hospital_id = serializers.UUIDField(source="hospital.id", allow_null=True, read_only=True)

    class Meta:
        model = Chamber
        fields = (
            "id", "doctor_id", "hospital", "hospital_id", "chamber_name",
            "address", "consultation_fee_override", "active",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "doctor_id", "hospital_id", "created_at", "updated_at",
        )
