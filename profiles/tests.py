from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from profiles.filters import ProfileFilter
from profiles.models import Profile
from profiles.templatetags.markdown_extras import markdown
from profiles.views import ProfileListView


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

    def test_text_search_is_ignored_without_business_access(self):
        create_profile("Django engineer")
        create_profile("React engineer")
        request = self.factory.get("/profiles/", {"title": "Django"})
        request.user = SimpleNamespace(is_authenticated=False)

        filterset = ProfileFilter(
            data=request.GET,
            queryset=Profile.objects.order_by("title"),
            request=request,
        )

        self.assertEqual(list(filterset.qs.values_list("title", flat=True)), ["Django engineer", "React engineer"])

    @patch("profiles.filters.has_active_subscription", return_value=True)
    def test_text_search_filters_with_business_access(self, _has_active_subscription):
        create_profile("Django engineer")
        create_profile("React engineer")
        request = self.factory.get("/profiles/", {"title": "Django"})
        request.user = SimpleNamespace(is_authenticated=True)

        filterset = ProfileFilter(
            data=request.GET,
            queryset=Profile.objects.order_by("title"),
            request=request,
        )

        self.assertEqual(list(filterset.qs.values_list("title", flat=True)), ["Django engineer"])

    def test_pagination_preserves_non_title_filters(self):
        for index in range(12):
            create_profile(f"New York engineer {index}", city="New York")
        create_profile("Austin engineer", city="Austin")
        request = self.factory.get("/profiles/", {"city": "New York"})
        request.user = AnonymousUser()

        response = ProfileListView.as_view()(request)

        self.assertEqual(response.context_data["profile_querystring"], "city=New+York")
        self.assertTrue(response.context_data["page_obj"].has_next())


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
