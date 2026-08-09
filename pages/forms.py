from urllib.parse import urlsplit

from django import forms
from django.core.exceptions import ValidationError


def validate_job_url(url):
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("Enter a valid http or https job page URL.")

    if parsed.username or parsed.password:
        raise ValidationError("Job links cannot include credentials.")

    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname or hostname == "localhost" or hostname.endswith((".local", ".internal")):
        raise ValidationError("Enter a link to a public job page.")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise ValidationError("Enter a valid job page URL.") from error

    if port not in (80, 443):
        raise ValidationError("Job links must use a standard web port.")

    return url


class JobMatchForm(forms.Form):
    job_url = forms.URLField(
        label="Job description link",
        max_length=2048,
        widget=forms.URLInput(
            attrs={
                "autocomplete": "url",
                "placeholder": "jobs.yourcompany.com/backend-engineer",
            }
        ),
    )

    def clean_job_url(self):
        return validate_job_url(self.cleaned_data["job_url"])
