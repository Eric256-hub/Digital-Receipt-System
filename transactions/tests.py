from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Business, BusinessMembership, Receipt, Transaction, TransactionItem


class AuthenticationEntryTests(TestCase):
    def test_home_offers_sign_in_and_account_creation(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Login")
        self.assertContains(response, "Create Account")

    def test_signed_in_home_does_not_offer_create_account_link(self):
        user = User.objects.create_user(username="signed-in-user", password="StrongPass!234")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Open Dashboard")
        self.assertContains(response, "Sign out")
        self.assertNotContains(response, "Create Account")

    def test_sign_out_clears_session_and_redirects_to_login(self):
        user = User.objects.create_user(username="logout-user", password="StrongPass!234")
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            dashboard_response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )
        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, "Login")
        self.assertContains(home_response, "Create Account")

    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_registration_renders_account_creation_form(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, "Create your account")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'data-password-toggle="id_password1"')
        self.assertContains(response, 'data-password-toggle="id_password2"')
        self.assertContains(response, 'data-password-rule="length"')
        self.assertContains(response, "Common-password checks are verified securely")
        self.assertContains(response, f'href="{reverse("home")}"')
        self.assertContains(response, "Explore the landing page")

    def test_login_page_offers_landing_page_link(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, 'data-password-toggle="password"')
        self.assertContains(response, f'href="{reverse("home")}"')
        self.assertContains(response, "Explore the landing page")

    def test_login_form_preserves_requested_destination(self):
        requested_page = reverse("dashboard")
        response = self.client.get(requested_page)
        self.assertEqual(response.status_code, 302)
        login_page = self.client.get(response.url)
        self.assertContains(login_page, f'name="next" value="{requested_page}"')

        user = User.objects.create_user(username="returning-user", password="StrongPass!234")
        response = self.client.post(reverse("login"), {
            "username": "returning-user",
            "password": "StrongPass!234",
            "next": requested_page,
        })

        self.assertRedirects(response, requested_page, fetch_redirect_response=False)
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class TransactionWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operator", password="StrongPass!234")
        self.business = Business.objects.create(business_name="Test Traders")
        BusinessMembership.objects.create(business=self.business, user=self.user, role="ADMIN")
        self.client.force_login(self.user)

    def test_dashboard_shows_business_metrics(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Traders")
        self.assertContains(response, "Today's recorded sales")

    def test_create_transaction_calculates_total_and_creates_receipt(self):
        response = self.client.post(reverse("transaction_create"), {
            "customer_name": "Amina",
            "customer_phone": "0700000000",
            "payment_method": "CASH",
            "item_description[]": ["Rice", "Sugar"],
            "quantity[]": ["2", "3"],
            "unit_price[]": ["5000", "4000"],
        })
        record = Transaction.objects.get(business=self.business)
        self.assertRedirects(response, reverse("receipt_detail", args=[record.pk]))
        self.assertEqual(record.total_amount, Decimal("22000.00"))
        self.assertEqual(record.items.count(), 2)
        self.assertTrue(Receipt.objects.filter(transaction=record).exists())

    def test_transaction_history_is_scoped_to_members_business(self):
        other_business = Business.objects.create(business_name="Another Shop")
        other_record = Transaction.objects.create(
            business=other_business,
            recorded_by=self.user,
            receipt_number="OTHER-001",
            payment_method="CASH",
            total_amount=Decimal("1000.00"),
        )
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, other_record.receipt_number)

    def test_cancellation_keeps_original_transaction_and_reason(self):
        record = Transaction.objects.create(
            business=self.business,
            recorded_by=self.user,
            receipt_number="TEST-RECEIPT-001",
            payment_method="CASH",
            total_amount=Decimal("7500.00"),
        )
        response = self.client.post(reverse("transaction_cancel", args=[record.pk]), {
            "cancellation_reason": "Customer returned the purchase"
        })
        record.refresh_from_db()
        self.assertRedirects(response, reverse("receipt_detail", args=[record.pk]))
        self.assertEqual(record.status, "CANCELLED")
        self.assertEqual(record.cancellation_reason, "Customer returned the purchase")
        self.assertTrue(Transaction.objects.filter(pk=record.pk).exists())

    def test_invalid_transaction_is_not_saved(self):
        response = self.client.post(reverse("transaction_create"), {
            "payment_method": "CASH",
            "item_description[]": ["Rice"],
            "quantity[]": ["-2"],
            "unit_price[]": ["5000"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.filter(business=self.business).count(), 0)
