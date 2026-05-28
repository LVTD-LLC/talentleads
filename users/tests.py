from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse_lazy

from users import views


class StripeIntegrationSmokeTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("users.views.stripe.checkout.Session.create")
    @patch("users.views.models.Customer.objects.get")
    @patch("users.views.models.Price.objects.all")
    def test_create_checkout_session_uses_current_stripe_checkout_api(
        self, price_objects_all, customer_get, checkout_session_create
    ):
        price_objects_all.return_value.first.return_value = SimpleNamespace(id="price_123")
        customer_get.return_value = SimpleNamespace(id="cus_123")
        checkout_session_create.return_value = SimpleNamespace(url="https://checkout.stripe.com/c/session")
        request = self.factory.post("/users/create-checkout-session")
        request.user = SimpleNamespace()

        response = views.create_checkout_session(request)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "https://checkout.stripe.com/c/session")
        checkout_session_create.assert_called_once_with(
            line_items=[
                {
                    "quantity": 1,
                    "price": "price_123",
                }
            ],
            mode="subscription",
            success_url=request.build_absolute_uri(reverse_lazy("profiles")) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse_lazy("home")) + "?status=failed",
            customer="cus_123",
            metadata={"price_id": "price_123"},
            allow_promotion_codes=True,
            automatic_tax={"enabled": True},
            customer_update={
                "address": "auto",
            },
            payment_method_types=["card"],
        )

    @patch("users.views.stripe.Customer.retrieve", return_value={"id": "cus_123"})
    @patch("users.views.models.Customer.sync_from_stripe_data")
    def test_successful_payment_webhook_syncs_djstripe_customer(self, sync_from_stripe_data, customer_retrieve):
        event = SimpleNamespace(type="checkout.session.completed", data={"object": {"customer": "cus_123"}})

        response = views.successfull_payment_webhook(event)

        self.assertEqual(response.status_code, 200)
        customer_retrieve.assert_called_once_with("cus_123")
        sync_from_stripe_data.assert_called_once_with({"id": "cus_123"})

    @patch("users.views.stripe.billing_portal.Session.create")
    @patch("users.views.models.Customer.objects.get")
    def test_create_customer_portal_session_uses_current_stripe_portal_api(self, customer_get, portal_session_create):
        customer_get.return_value = SimpleNamespace(id="cus_123")
        portal_session_create.return_value = SimpleNamespace(url="https://billing.stripe.com/session")
        request = self.factory.post("/users/customer-portal")
        request.user = Mock()

        response = views.create_customer_portal_session(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://billing.stripe.com/session")
        portal_session_create.assert_called_once_with(
            customer="cus_123",
            return_url=request.build_absolute_uri(reverse_lazy("home")),
        )
