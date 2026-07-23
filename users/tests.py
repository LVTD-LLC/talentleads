from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class OutreachTemplateAccessTests(TestCase):
    @patch(
        "webpack_boilerplate.loader.WebpackLoader.load_assets",
        return_value={"entrypoints": {"index": {"assets": {"js": [], "css": []}}}},
    )
    def test_authenticated_user_can_render_template_form_without_subscription(self, _load_assets):
        user = get_user_model().objects.create_user(
            username="founder",
            email="founder@example.com",
            password="test",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("templates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create a new template")
        self.assertNotContains(response, "business access")
