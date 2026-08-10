from django.urls import path
from django.views.generic import TemplateView

from .views import HomeView, JobMatchView, ProductHuntView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("match/", JobMatchView.as_view(), name="job-match"),
    path("product-hunt", ProductHuntView.as_view(), name="product-hunt"),
    path("pricing", TemplateView.as_view(template_name="pages/pricing.html"), name="pricing"),
]
