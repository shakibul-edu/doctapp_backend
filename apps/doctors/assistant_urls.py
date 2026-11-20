from django.urls import path

from .views import AssistantDoctorsView

urlpatterns = [
    path("me/doctors/", AssistantDoctorsView.as_view(), name="assistant-doctors"),
]
