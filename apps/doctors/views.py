from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response

from apps.accounts.permissions import IsAssistant, IsDoctor
from .models import DoctorAssistant, DoctorProfile
from .serializers import (
    DoctorAssistantCreateSerializer,
    DoctorAssistantSerializer,
    DoctorPublicSerializer,
    DoctorWriteSerializer,
)


class DoctorListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DoctorPublicSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("professional_name", "specialty", "qualifications", "languages")
    ordering_fields = (
        "professional_name", "experience_years", "consultation_fee", "created_at",
    )
    filterset_fields = ("specialty", "experience_years", "consultation_fee")

    def get_queryset(self):
        qs = DoctorProfile.objects.filter(
            verification_status=DoctorProfile.VerificationStatus.APPROVED
        ).prefetch_related("chambers")
        hospital = self.request.query_params.get("hospital")
        if hospital:
            qs = qs.filter(chambers__hospital_id=hospital, chambers__active=True).distinct()
        location = self.request.query_params.get("location")
        if location:
            qs = qs.filter(chambers__address__icontains=location, chambers__active=True).distinct()
        return qs


class DoctorDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DoctorPublicSerializer
    lookup_field = "id"

    def get_queryset(self):
        return DoctorProfile.objects.filter(
            verification_status=DoctorProfile.VerificationStatus.APPROVED
        ).prefetch_related("chambers")


class DoctorMeView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsDoctor,)

    def get_object(self):
        profile, _ = DoctorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "professional_name": self.request.user.full_name,
                "specialty": "",
                "medical_registration_number": f"PENDING-{self.request.user.id}",
            },
        )
        return profile

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return DoctorWriteSerializer
        return DoctorPublicSerializer


class DoctorAssistantListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsDoctor,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DoctorAssistantCreateSerializer
        return DoctorAssistantSerializer

    def get_queryset(self):
        profile = getattr(self.request.user, "doctor_profile", None)
        if profile is None:
            return DoctorAssistant.objects.none()
        return DoctorAssistant.objects.filter(doctor=profile).select_related("assistant")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        profile = getattr(request.user, "doctor_profile", None)
        if profile is None:
            return Response(
                {"detail": "Create your doctor profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assistant = serializer.validated_data["assistant_id"]
        relationship, created = DoctorAssistant.objects.update_or_create(
            doctor=profile,
            assistant=assistant,
            defaults={
                "active": serializer.validated_data["active"],
                "can_view_patient_profiles": serializer.validated_data["can_view_patient_profiles"],
                "can_manage_chambers": serializer.validated_data["can_manage_chambers"],
            },
        )
        output = DoctorAssistantSerializer(relationship, context={"request": request})
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DoctorAssistantDeleteView(generics.DestroyAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = DoctorAssistantSerializer
    lookup_field = "id"

    def get_queryset(self):
        profile = getattr(self.request.user, "doctor_profile", None)
        if profile is None:
            return DoctorAssistant.objects.none()
        return DoctorAssistant.objects.filter(doctor=profile)


class AssistantDoctorsView(generics.ListAPIView):
    permission_classes = (IsAssistant,)
    serializer_class = DoctorPublicSerializer

    def get_queryset(self):
        doctor_ids = DoctorAssistant.objects.filter(
            assistant=self.request.user,
            active=True,
        ).values("doctor_id")
        return DoctorProfile.objects.filter(id__in=doctor_ids).prefetch_related("chambers")
