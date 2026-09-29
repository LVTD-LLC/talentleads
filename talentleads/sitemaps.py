from django.contrib import sitemaps
from django.contrib.sitemaps import GenericSitemap
from django.urls import reverse

from blog.models import BlogPost
from blog.choices import BlogPostStatus


class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5

    def items(self):
        return ["home", "pricing", "profiles", "blog_posts"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "sitemaps": {
        "static": StaticViewSitemap,
        "blog": GenericSitemap(
            {
                "queryset": BlogPost.objects.filter(status=BlogPostStatus.PUBLISHED),
                "date_field": "modified",
            }
        ),
    }
}
