import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from django.core.exceptions import ValidationError
from pgvector.django import CosineDistance

from profiles.models import Profile
from profiles.tasks import get_jina_embedding

from .forms import validate_public_job_url

MAX_JOB_PAGE_BYTES = 500_000
MAX_JOB_TEXT_CHARACTERS = 16_000
MAX_REDIRECTS = 3


class JobPageFetchError(Exception):
    pass


class JobPageTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.excluded_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.excluded_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.excluded_depth:
            self.excluded_depth -= 1

    def handle_data(self, data):
        if not self.excluded_depth:
            self.parts.append(data)

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def extract_job_text(content, content_type):
    if "html" not in content_type:
        return re.sub(r"\s+", " ", content.decode("utf-8", errors="ignore")).strip()

    parser = JobPageTextParser()
    parser.feed(content.decode("utf-8", errors="ignore"))
    return parser.text()


def fetch_job_text(job_url):
    current_url = job_url
    headers = {"User-Agent": "TalentLeads job matcher/1.0"}

    try:
        with httpx.Client(headers=headers, timeout=10, follow_redirects=False, trust_env=False) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                try:
                    validate_public_job_url(current_url)
                except ValidationError as error:
                    raise JobPageFetchError(error.messages[0]) from error

                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        if redirect_count == MAX_REDIRECTS:
                            raise JobPageFetchError("That job page redirected too many times.")
                        location = response.headers.get("location")
                        if not location:
                            raise JobPageFetchError("That job page returned an invalid redirect.")
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml", "text/plain")):
                        raise JobPageFetchError("That link does not look like a readable job page.")

                    chunks = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_JOB_PAGE_BYTES:
                            raise JobPageFetchError("That job page is too large to read.")
                        chunks.append(chunk)
                    break
    except JobPageFetchError:
        raise
    except (httpx.HTTPError, OSError) as error:
        raise JobPageFetchError("We could not read that job page. Check the link and try again.") from error

    job_text = extract_job_text(b"".join(chunks), content_type)
    if len(job_text) < 100:
        raise JobPageFetchError("We could not find enough job details on that page.")

    return job_text[:MAX_JOB_TEXT_CHARACTERS]


def find_matching_profiles(job_url):
    job_text = fetch_job_text(job_url)
    embedding = get_jina_embedding(job_text)
    if not embedding:
        raise JobPageFetchError("We could not compare this role right now. Please try again.")

    return list(
        Profile.objects.filter(embedding__isnull=False)
        .annotate(match_distance=CosineDistance("embedding", embedding))
        .prefetch_related("tech_stack")
        .order_by("match_distance", "id")[:12]
    )
