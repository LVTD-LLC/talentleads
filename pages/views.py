from django.views.generic import TemplateView

from profiles.models import Profile
from talentleads.utils import floor_to_thousands, get_talentleads_logger
from utils.views import add_users_context

logger = get_talentleads_logger(__name__)


class HomeView(TemplateView):
    template_name = "pages/home.html"

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
