from rest_framework import generics

from apps.accounts.permissions import IsPatient
from .models import PatientProfile
from .permissions import IsPatientProfileOwner
from .serializers import PatientProfileSerializer


class PatientMeView(generics.RetrieveUpdateAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = (IsPatient, IsPatientProfileOwner)

    def get_object(self):
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        self.check_object_permissions(self.request, profile)
        return profile


class PatientDetailView(generics.RetrieveAPIView):
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientProfileSerializer
    permission_classes = (IsPatientProfileOwner,)
    lookup_field = "id"
