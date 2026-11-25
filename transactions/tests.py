from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Business, BusinessMembership, Receipt, Transaction, TransactionItem


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
