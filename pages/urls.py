from django.urls import path

from .views import HomeView, ProductHuntView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("product-hunt", ProductHuntView.as_view(), name="product-hunt"),
]
