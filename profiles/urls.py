from django.urls import path

from .views import ProfileDetailView, ProfileListView, TriggerAsyncTask, send_outreach_email

urlpatterns = [
    path("", ProfileListView.as_view(), name="profiles"),
    path("<uuid:pk>", ProfileDetailView.as_view(), name="profile"),
    path("trigger-task/", TriggerAsyncTask.as_view(), name="trigger_task"),
    path(
        "<uuid:profile_id>/send",
        send_outreach_email,
        name="send-email-to-profile",
    ),
]
