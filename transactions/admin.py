
from django.contrib import admin
from .models import (
    Business,
    BusinessMembership,
    Customer,
    Transaction,
    TransactionItem,
    Receipt,
)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'phone', 'address')
    search_fields = ('business_name', 'phone')


@admin.register(BusinessMembership)
class BusinessMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'business', 'role')
    list_filter = ('role', 'business')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'phone', 'business')
    search_fields = ('customer_name', 'phone')


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'receipt_number',
        'business',
        'transaction_date',
        'total_amount',
        'status',
    )
    list_filter = ('status', 'payment_method', 'business')
    search_fields = ('receipt_number',)
    inlines = [TransactionItemInline]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'issued_at', 'print_count')
