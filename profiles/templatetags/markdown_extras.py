# from Will Vincent tutorial -> https://learndjango.com/tutorials/django-markdown-tutorial

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import markdown as md
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()

extension_configs = {
    "markdown.extensions.codehilite": {
        "css_class": "codehilite",
        "linenums": False,
        "guess_lang": False,
    }
}

# Candidate descriptions are sourced from public profile text. Images are
# intentionally excluded to avoid hotlinked/tracking media in profile views.
ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "dd",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
    "div": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "td": {"align"},
    "th": {"align"},
}
SAFE_SCHEMES = {"", "http", "https", "mailto", "tel"}


class SanitizingHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            alt_text = next((value for name, value in attrs if name == "alt" and value), "")
            if alt_text:
                self.parts.append(escape(alt_text))
            return

        if tag not in ALLOWED_TAGS:
            return

        clean_attrs = []
        allowed_attrs = ALLOWED_ATTRIBUTES.get(tag, set())
        for name, value in attrs:
            if name not in allowed_attrs or value is None:
                continue
            if name == "href" and urlparse(value).scheme.lower() not in SAFE_SCHEMES:
                continue
            clean_attrs.append(f'{name}="{escape(value, quote=True)}"')

        attrs_text = f" {' '.join(clean_attrs)}" if clean_attrs else ""
        self.parts.append(f"<{tag}{attrs_text}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        self.parts.append(escape(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def get_html(self):
        return "".join(self.parts)


def sanitize_html(html):
    parser = SanitizingHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.get_html()


@register.filter()
@stringfilter
def markdown(value):
    html = md.markdown(
        value,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.codehilite",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ],
        extension_configs=extension_configs,
    )
    return mark_safe(sanitize_html(html))
