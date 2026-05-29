import stripe
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, UpdateView
from django_q.tasks import async_task
from djstripe import models, settings as djstripe_settings
from djstripe.event_handlers import djstripe_receiver

from talentleads.utils import get_talentleads_logger
from utils.views import add_users_context

from users.forms import CreateOutreachTemplateForm, SupportForm, UpdateOutreachTemplateForm
from users.models import CustomUser, OutreachTemplate
from users.tasks import email_support_request

stripe.api_key = djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY
logger = get_talentleads_logger(__name__)


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


def create_checkout_session(request):
    user = request.user
    price_id = models.Price.objects.all().first().id

    customer = models.Customer.objects.get(subscriber=user)

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "quantity": 1,
                "price": price_id,
            }
        ],
        mode="subscription",
        success_url=request.build_absolute_uri(reverse_lazy("profiles")) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse_lazy("home")) + "?status=failed",
        customer=customer.id,
        metadata={"price_id": price_id},
        allow_promotion_codes=True,
        automatic_tax={"enabled": True},
        customer_update={
            "address": "auto",
        },
        payment_method_types=["card"],
    )

    response = HttpResponse(status=303)
    response["Location"] = checkout_session.url
    return response


@djstripe_receiver("checkout.session.completed")
def successfull_payment_webhook(event, **kwargs):
    if event.type == "checkout.session.completed":
        customer = event.data["object"]["customer"]
        logger.info(f"Upgrading Customer: {customer}")
        models.Customer.sync_from_stripe_data(stripe.Customer.retrieve(customer))

    return HttpResponse(status=200)


def create_customer_portal_session(request):
    customer = models.Customer.objects.get(subscriber=request.user)
    session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=request.build_absolute_uri(reverse_lazy("home")),
    )

    return redirect(session.url)


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
