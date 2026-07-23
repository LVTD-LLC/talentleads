from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from profiles.filters import ProfileFilter
from profiles.models import Profile
from profiles.templatetags.markdown_extras import markdown
from profiles.views import ProfileListView
from users.models import Outreach, OutreachTemplate


def create_profile(title, description="Django engineer", city="New York"):
    return Profile.objects.create(
        latest_who_wants_to_be_hired_id=1,
        who_wants_to_be_hired_title="June 2026",
        title=title,
        description=description,
        city=city,
        country="United States",
        who_wants_to_be_hired_comment_id=Profile.objects.count() + 1,
    )


class ProfileSearchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_text_search_filters_without_subscription(self):
        create_profile("Django engineer")
        create_profile("React engineer")
        request = self.factory.get("/profiles/", {"title": "Django"})
        request.user = SimpleNamespace(is_authenticated=False)

        filterset = ProfileFilter(
            data=request.GET,
            queryset=Profile.objects.order_by("title"),
            request=request,
        )

        self.assertEqual(list(filterset.qs.values_list("title", flat=True)), ["Django engineer"])

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    @patch(
        "webpack_boilerplate.loader.WebpackLoader.load_assets",
        return_value={"entrypoints": {"index": {"assets": {"js": [], "css": []}}}},
    )
    def test_authenticated_profile_search_renders_without_payment_integration(self, _load_assets):
        create_profile("Django engineer")
        create_profile("React engineer")
        user = get_user_model().objects.create_user(username="founder", email="founder@example.com", password="test")
        self.client.force_login(user)

        response = self.client.get("/profiles/", {"title": "Django"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django engineer")
        self.assertNotContains(response, "React engineer")

    def test_pagination_preserves_non_title_filters(self):
        for index in range(12):
            create_profile(f"New York engineer {index}", city="New York")
        create_profile("Austin engineer", city="Austin")
        request = self.factory.get("/profiles/", {"city": "New York"})
        request.user = AnonymousUser()

        response = ProfileListView.as_view()(request)

        self.assertEqual(response.context_data["profile_querystring"], "city=New+York")
        self.assertTrue(response.context_data["page_obj"].has_next())


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@patch(
    "webpack_boilerplate.loader.WebpackLoader.load_assets",
    return_value={"entrypoints": {"index": {"assets": {"js": [], "css": []}}}},
)
class ProfileAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="founder",
            email="founder@example.com",
            password="test",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other",
            email="other@example.com",
            password="test",
        )
        self.profile = create_profile("Django engineer")
        self.profile.email = "candidate@example.com"
        self.profile.name = "Candidate Name"
        self.profile.save(update_fields=["email", "name"])
        self.template = OutreachTemplate.objects.create(
            author=self.user,
            title="Introduction",
            subject_line="A role for you",
            text="Hello!",
        )

    def test_private_contact_details_require_login(self, _load_assets):
        response = self.client.get(reverse("profile", kwargs={"pk": self.profile.id}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.profile.email)
        self.assertContains(response, "Log in to view contact details")

    def test_authenticated_user_sees_contact_and_outreach_form(self, _load_assets):
        self.client.force_login(self.user)

        response = self.client.get(reverse("profile", kwargs={"pk": self.profile.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.profile.email)
        self.assertContains(response, self.template.title)
        self.assertContains(response, reverse("send-email-to-profile", kwargs={"profile_id": self.profile.id}))

    def test_outreach_requires_login(self, _load_assets):
        outreach_url = reverse("send-email-to-profile", kwargs={"profile_id": self.profile.id})

        response = self.client.post(outreach_url, {"email_template_id": self.template.id})

        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={outreach_url}",
            fetch_redirect_response=False,
        )
        self.assertFalse(Outreach.objects.exists())

    def test_outreach_rejects_get(self, _load_assets):
        self.client.force_login(self.user)

        response = self.client.get(reverse("send-email-to-profile", kwargs={"profile_id": self.profile.id}))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Outreach.objects.exists())

    def test_outreach_rejects_another_users_template(self, _load_assets):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("send-email-to-profile", kwargs={"profile_id": self.profile.id}),
            {"email_template_id": self.template.id},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Outreach.objects.exists())


class MarkdownFilterTests(TestCase):
    def test_markdown_escapes_raw_html(self):
        rendered = str(markdown("<script>alert('xss')</script>"))

        self.assertNotIn("<script>", rendered)
        self.assertIn("alert", rendered)

    def test_markdown_drops_unsafe_link_protocols(self):
        rendered = str(markdown("[bad](javascript:alert(1))"))

        self.assertNotIn("javascript:", rendered)

    def test_markdown_preserves_code_span_special_characters(self):
        rendered = str(markdown("`a < b && c > d`"))

        self.assertIn("<code>a &lt; b &amp;&amp; c &gt; d</code>", rendered)
        self.assertNotIn("&amp;lt;", rendered)

    def test_markdown_strips_images_from_profile_descriptions(self):
        rendered = str(markdown("![tracking pixel](https://example.com/pixel.gif)"))

        self.assertNotIn("<img", rendered)
        self.assertIn("tracking pixel", rendered)
