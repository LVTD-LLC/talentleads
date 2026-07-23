from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, UpdateView
from django_q.tasks import async_task

from utils.views import add_users_context

from users.forms import CreateOutreachTemplateForm, SupportForm, UpdateOutreachTemplateForm
from users.models import CustomUser, OutreachTemplate
from users.tasks import email_support_request


class UserSettingsView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    login_url = "account_login"
    model = CustomUser
    fields = ["name", "email"]
    success_message = "Profile updated."
    success_url = reverse_lazy("settings")
    template_name = "account/settings.html"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        add_users_context(context, user)

        return context


def resend_email_confirmation_email(request):
    user = request.user
    adapter = get_adapter(request)
    emailaddress = EmailAddress.objects.get_for_user(user, user.email)
    adapter.send_confirmation_mail(request, emailaddress, signup=False)

    return redirect("settings")


class SupportView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    login_url = "account_login"
    template_name = "account/support.html"
    form_class = SupportForm

    def get_success_url(self):
        messages.add_message(
            self.request,
            messages.INFO,
            "Thanks for the note. I'll follow up by email if I need more detail.",
        )
        return reverse_lazy("support")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        if user.is_authenticated:
            add_users_context(context, user)

        return context

    def form_valid(self, form):
        async_task(email_support_request, form.cleaned_data, hook="users.hooks.email_sent")
        return super(SupportView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user
        return kwargs


class TemplateCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    login_url = "account_login"
    model = OutreachTemplate
    form_class = CreateOutreachTemplateForm
    template_name = "account/create-outreach-template.html"
    success_url = reverse_lazy("templates")
    success_message = "Outreach template created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        context["templates"] = OutreachTemplate.objects.filter(author=user)
        context["update_form"] = UpdateOutreachTemplateForm

        if user.is_authenticated:
            add_users_context(context, user)

        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        self.object = form.save()

        return super(TemplateCreateView, self).form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    login_url = "account_login"
    model = OutreachTemplate
    form_class = UpdateOutreachTemplateForm
    template_name = "account/update-outreach-template.html"
    success_url = reverse_lazy("templates")
    success_message = "Outreach template updated."

    def post(self, request, *args, **kwargs):
        if "delete_object" in request.POST:
            return self.delete(request, *args, **kwargs)
        else:
            return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        messages.success(request, "Outreach template deleted.")
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)
