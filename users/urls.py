from django.urls import path

from .views import (
    SupportView,
    TemplateCreateView,
    TemplateUpdateView,
    UserSettingsView,
    resend_email_confirmation_email,
)

urlpatterns = [
    path("settings/", UserSettingsView.as_view(), name="settings"),
    path("support", SupportView.as_view(), name="support"),
    path("templates", TemplateCreateView.as_view(), name="templates"),
    path(
        "template/<uuid:pk>/update",
        TemplateUpdateView.as_view(),
        name="update-template",
    ),
    path(
        "send-confirmation",
        resend_email_confirmation_email,
        name="resend_email_confirmation_email",
    ),
]
