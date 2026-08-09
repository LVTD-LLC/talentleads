from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import FormView, TemplateView

from profiles.models import Profile
from talentleads.utils import floor_to_thousands, get_talentleads_logger
from utils.views import add_users_context

from .forms import JobMatchForm
from .services import JobPageFetchError, find_matching_profiles

logger = get_talentleads_logger(__name__)


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["num_of_profiles"] = floor_to_thousands(len(Profile.objects.all()))
        context["job_match_form"] = JobMatchForm()

        if user.is_authenticated:
            add_users_context(context, user)

        return context


class JobMatchView(LoginRequiredMixin, FormView):
    login_url = "account_login"
    http_method_names = ["post"]
    form_class = JobMatchForm
    template_name = "pages/home.html"

    def form_valid(self, form):
        job_url = form.cleaned_data["job_url"]
        try:
            matches = find_matching_profiles(job_url)
        except JobPageFetchError as error:
            form.add_error("job_url", str(error))
            return self.form_invalid(form)

        return render(
            self.request,
            "pages/job_matches.html",
            {"job_url": job_url, "matches": matches},
        )

    def form_invalid(self, form):
        return render(
            self.request,
            self.template_name,
            {
                "job_match_form": form,
                "num_of_profiles": floor_to_thousands(Profile.objects.count()),
            },
            status=422,
        )


class ProductHuntView(TemplateView):
    template_name = "pages/product_hunt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["profiles"] = (
            Profile.objects.exclude(description__isnull=True).exclude(description__exact="").order_by("-created")[:8]
        )
        context["num_of_profiles"] = floor_to_thousands(len(Profile.objects.all()))

        if user.is_authenticated:
            add_users_context(context, user)

        return context
