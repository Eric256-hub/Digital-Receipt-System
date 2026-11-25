
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Business(models.Model):
    business_name = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    receipt_footer = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.business_name


class BusinessMembership(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('OPERATOR', 'Business Operator'),
    ]

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='business_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'user'],
                name='unique_business_membership'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.business.business_name}"


class Customer(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE
    )
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.customer_name


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK', 'Bank'),
        ('OTHER', 'Other'),
    ]

    business = models.ForeignKey(
        Business, on_delete=models.PROTECT
    )
    recorded_by = models.ForeignKey(
        User, on_delete=models.PROTECT
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    receipt_number = models.CharField(max_length=40)
    transaction_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='COMPLETED'
    )
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cancelled_transactions'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'receipt_number'],
                name='unique_business_receipt_number'
            )
        ]
        ordering = ['-transaction_date']

    def __str__(self):
        return self.receipt_number


class TransactionItem(models.Model):
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE,
        related_name='items'
    )
    item_description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    line_total = models.DecimalField(
        max_digits=12, decimal_places=2
    )

    def __str__(self):
        return self.item_description


class Receipt(models.Model):
    transaction = models.OneToOneField(
        Transaction, on_delete=models.PROTECT,
        related_name='receipt'
    )
    issued_at = models.DateTimeField(default=timezone.now)
    print_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Receipt {self.transaction.receipt_number}"
