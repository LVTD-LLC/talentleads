from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView
from django_filters.views import FilterView
from django_q.tasks import async_task

from talentleads.utils import floor_to_tens, get_talentleads_logger
from users.models import Outreach, OutreachTemplate
from utils.views import add_users_context

from .filters import ProfileFilter
from .models import Profile
from .tasks import get_hn_pages_to_analyze, send_outreach_email_task

logger = get_talentleads_logger(__name__)


class ProfileListView(LoginRequiredMixin, FilterView):
    login_url = "account_login"
    model = Profile
    template_name = "profiles/all_profiles.html"
    queryset = Profile.objects.prefetch_related("tech_stack").order_by("-created", "-id")
    filterset_class = ProfileFilter
    paginate_by = 11

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["num_of_profiles"] = floor_to_tens(Profile.objects.count())
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["profile_querystring"] = query_params.urlencode()

        user = self.request.user
        if user.is_authenticated:
            add_users_context(context, user)

        return context


class ProfileDetailView(LoginRequiredMixin, DetailView):
    login_url = "account_login"
    model = Profile
    template_name = "profiles/profile_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        if user.is_authenticated:
            add_users_context(context, user)
            outreach_templates = OutreachTemplate.objects.filter(author=user).order_by("title")
            context["outreach_templates"] = outreach_templates

        if self.object:
            context["profile_capacity"] = [item.strip() for item in self.object.capacity.split(",") if item.strip()]

        return context


class GenericForm(forms.Form):
    who_wants_to_be_hired_post_id = forms.CharField()


class TriggerAsyncTask(LoginRequiredMixin, UserPassesTestMixin, FormView):
    login_url = "account_login"
    success_url = reverse_lazy("home")
    template_name = "profiles/trigger_task.html"
    form_class = GenericForm

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        who_wants_to_be_hired_post_id = form.cleaned_data.get("who_wants_to_be_hired_post_id")
        async_task(get_hn_pages_to_analyze, who_wants_to_be_hired_post_id, hook="profiles.hooks.print_result")
        return super(TriggerAsyncTask, self).form_valid(form)


@login_required(login_url="account_login")
@require_POST
def send_outreach_email(request, profile_id):
    email_template_id = request.POST.get("email_template")
    logger.info(f"profile_id: {profile_id}")
    logger.info(f"email_template_id: {email_template_id}")

    user = request.user
    profile = get_object_or_404(Profile, id=profile_id)

    if not profile.email:
        messages.add_message(request, messages.WARNING, "This profile does not have an email address yet.")
        return redirect(reverse("profile", kwargs={"pk": profile_id}))

    template = get_object_or_404(OutreachTemplate, id=email_template_id, author=user)

    obj, created = Outreach.objects.get_or_create(author=user, receiver=profile, template=template)
    logger.info(f"obj, created: {obj}, {created}")

    if created:
        async_task(
            send_outreach_email_task,
            template.subject_line,
            template.text,
            profile.email,
            user,
            template.cc_s,
            hook="profiles.hooks.email_sent",
        )
        messages.add_message(request, messages.INFO, "Outreach email queued. Check your inbox for the CC.")
    else:
        messages.add_message(
            request, messages.WARNING, "You have already sent outreach to this candidate with that template."
        )

    return redirect(reverse("profile", kwargs={"pk": profile_id}))
