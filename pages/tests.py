import socket
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from pages.forms import JobMatchForm
from pages.services import find_matching_profiles, validate_public_job_url
from profiles.models import Profile


class JobMatchFormTests(SimpleTestCase):
    def test_accepts_public_http_url(self):
        form = JobMatchForm({"job_url": "https://jobs.example.com/backend-engineer"})

        self.assertTrue(form.is_valid())

    def test_rejects_localhost(self):
        form = JobMatchForm({"job_url": "http://localhost:8000/private"})

        self.assertFalse(form.is_valid())
        self.assertIn("public job page", form.errors["job_url"][0])

    def test_rejects_non_web_scheme(self):
        form = JobMatchForm({"job_url": "ftp://jobs.example.com/backend-engineer"})

        self.assertFalse(form.is_valid())
        self.assertIn("http or https", form.errors["job_url"][0])

    @patch("pages.services.socket.getaddrinfo")
    def test_rejects_private_network_address(self, getaddrinfo):
        getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.8", 443))]

        with self.assertRaisesMessage(ValidationError, "public job page"):
            validate_public_job_url("https://jobs.example.com/backend-engineer")

    def test_rejects_url_credentials(self):
        form = JobMatchForm({"job_url": "https://user:password@jobs.example.com/role"})

        self.assertFalse(form.is_valid())
        self.assertIn("credentials", form.errors["job_url"][0])


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class JobMatchViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="founder", password="password")

    def test_home_renders_job_url_form_and_auth_prompt(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'name="job_url"')
        self.assertContains(response, 'id="signup-required-dialog"')
        self.assertContains(response, "Free to use. Account required.")

    def test_anonymous_match_request_requires_login(self):
        response = self.client.post(
            reverse("job-match"),
            {"job_url": "https://jobs.example.com/backend-engineer"},
        )

        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('job-match')}",
            fetch_redirect_response=False,
        )

    @patch("pages.views.find_matching_profiles")
    def test_authenticated_user_gets_matching_people(self, find_matching_profiles):
        find_matching_profiles.return_value = [
            SimpleNamespace(
                title="Senior Django engineer",
                description="Built APIs for early-stage teams.",
                location="Remote",
                get_absolute_url=lambda: "/profiles/00000000-0000-0000-0000-000000000001",
            )
        ]
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("job-match"),
            {"job_url": "https://jobs.example.com/backend-engineer"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/job_matches.html")
        self.assertContains(response, "Senior Django engineer")
        find_matching_profiles.assert_called_once_with("https://jobs.example.com/backend-engineer")


class ProfileMatchingTests(TestCase):
    @patch("pages.services.get_jina_embedding")
    @patch("pages.services.fetch_job_text", return_value="Senior Python backend engineer for an early-stage team.")
    def test_profiles_are_ranked_by_embedding_similarity(self, _fetch_job_text, get_jina_embedding):
        matching_embedding = [1.0] + [0.0] * 1023
        unrelated_embedding = [0.0, 1.0] + [0.0] * 1022
        get_jina_embedding.return_value = matching_embedding
        close_match = Profile.objects.create(
            latest_who_wants_to_be_hired_id=1,
            who_wants_to_be_hired_title="June 2026",
            who_wants_to_be_hired_comment_id=1,
            title="Python backend engineer",
            embedding=matching_embedding,
        )
        Profile.objects.create(
            latest_who_wants_to_be_hired_id=1,
            who_wants_to_be_hired_title="June 2026",
            who_wants_to_be_hired_comment_id=2,
            title="Product designer",
            embedding=unrelated_embedding,
        )

        matches = find_matching_profiles("https://jobs.example.com/backend-engineer")

        self.assertEqual(matches[0], close_match)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class PublicPageTests(TestCase):
    @patch(
        "webpack_boilerplate.loader.WebpackLoader.load_assets",
        return_value={"entrypoints": {"index": {"assets": {"js": [], "css": []}}}},
    )
    def test_pricing_describes_current_free_access(self, _load_assets):
        response = self.client.get(reverse("pricing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "$0")
        self.assertContains(response, "No credit card")
