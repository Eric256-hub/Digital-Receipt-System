from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction as db_transaction
from django.db.models import F, Q, Sum
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Business, BusinessMembership, Customer, Receipt,
    Transaction, TransactionItem,
)


def _membership_for(user):
    return (
        BusinessMembership.objects
        .select_related("business")
        .filter(user=user)
        .first()
    )


def home(request):
    return render(request, "transactions/home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account is ready. Set up your business to continue.")
        return redirect("business_setup")
    return render(request, "transactions/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = authenticate(request, username=username, password=request.POST.get("password", ""))
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "The username or password you entered is incorrect.")
    return render(request, "transactions/login.html")


@login_required(login_url="login")
def dashboard(request):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    business = membership.business
    today = timezone.localdate()
    transactions = Transaction.objects.filter(business=business)
    today_transactions = transactions.filter(transaction_date__date=today)
    completed = transactions.filter(status="COMPLETED")
    context = {
        "business": business,
        "total_count": transactions.count(),
        "completed_count": completed.count(),
        "receipt_count": Receipt.objects.filter(transaction__business=business).count(),
        "today_total": today_transactions.filter(status="COMPLETED").aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00"),
        "recent_transactions": transactions.select_related("customer", "recorded_by")[:8],
    }
    return render(request, "transactions/dashboard.html", context)


@login_required(login_url="login")
def business_setup(request):
    if _membership_for(request.user):
        return redirect("dashboard")
    if request.method == "POST":
        name = request.POST.get("business_name", "").strip()
        if not name:
            messages.error(request, "Enter your business name.")
        else:
            with db_transaction.atomic():
                business = Business.objects.create(
                    business_name=name,
                    address=request.POST.get("address", "").strip(),
                    phone=request.POST.get("phone", "").strip(),
                    receipt_footer=request.POST.get("receipt_footer", "").strip(),
                )
                BusinessMembership.objects.create(business=business, user=request.user, role="ADMIN")
            messages.success(request, "Business profile created successfully.")
            return redirect("dashboard")
    return render(request, "transactions/business_setup.html")


@login_required(login_url="login")
def transaction_list(request):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    qs = Transaction.objects.filter(business=membership.business).select_related("customer", "recorded_by")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    start = request.GET.get("from", "").strip()
    end = request.GET.get("to", "").strip()
    if query:
        qs = qs.filter(Q(receipt_number__icontains=query) | Q(customer__customer_name__icontains=query))
    if status in {"COMPLETED", "CANCELLED"}:
        qs = qs.filter(status=status)
    try:
        if start:
            date.fromisoformat(start)
            qs = qs.filter(transaction_date__date__gte=start)
        if end:
            date.fromisoformat(end)
            qs = qs.filter(transaction_date__date__lte=end)
        if start and end and date.fromisoformat(end) < date.fromisoformat(start):
            raise ValueError
    except ValueError:
        messages.error(request, "Enter a valid date range.")
        start, end = "", ""
        qs = Transaction.objects.filter(business=membership.business).select_related("customer", "recorded_by")
    return render(request, "transactions/transaction_list.html", {
        "transactions": qs[:200], "query": query, "status": status,
        "date_from": start, "date_to": end,
    })


@login_required(login_url="login")
def transaction_create(request):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    if request.method == "POST":
        descriptions = request.POST.getlist("item_description[]")
        quantities = request.POST.getlist("quantity[]")
        prices = request.POST.getlist("unit_price[]")
        valid_items = []
        errors = []
        for index, description in enumerate(descriptions):
            description = description.strip()
            if not description and index >= len(quantities):
                continue
            try:
                quantity = Decimal(quantities[index])
                price = Decimal(prices[index])
                if (
                    not description or not quantity.is_finite() or not price.is_finite()
                    or quantity <= 0 or quantity > Decimal("99999999.99")
                    or price < 0 or price > Decimal("9999999999.99")
                ):
                    raise InvalidOperation
                line_total = (quantity * price).quantize(Decimal("0.01"))
                if line_total > Decimal("9999999999.99"):
                    raise InvalidOperation
                valid_items.append((description, quantity, price, line_total))
            except (InvalidOperation, ValueError, IndexError):
                errors.append(f"Check item row {index + 1}: enter a description, positive quantity and valid price.")
        if not valid_items:
            errors.append("Add at least one valid transaction item.")
        payment = request.POST.get("payment_method", "CASH")
        if payment not in dict(Transaction.PAYMENT_CHOICES):
            errors.append("Choose a valid payment method.")
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "transactions/transaction_form.html", {"payment_choices": Transaction.PAYMENT_CHOICES})
        customer_name = request.POST.get("customer_name", "").strip()
        customer_phone = request.POST.get("customer_phone", "").strip()
        with db_transaction.atomic():
            customer = None
            if customer_name:
                customer, _ = Customer.objects.get_or_create(
                    business=membership.business,
                    customer_name=customer_name,
                    defaults={"phone": customer_phone},
                )
            receipt_number = f"DRS-{timezone.localdate():%Y%m%d}-{uuid4().hex[:8].upper()}"
            total = sum((item[3] for item in valid_items), Decimal("0.00"))
            if total > Decimal("9999999999.99"):
                messages.error(request, "The transaction total is above the supported limit.")
                return render(request, "transactions/transaction_form.html", {"payment_choices": Transaction.PAYMENT_CHOICES})
            record = Transaction.objects.create(
                business=membership.business,
                recorded_by=request.user,
                customer=customer,
                receipt_number=receipt_number,
                payment_method=payment,
                total_amount=total,
            )
            TransactionItem.objects.bulk_create([
                TransactionItem(transaction=record, item_description=desc,
                                 quantity=qty, unit_price=price, line_total=line)
                for desc, qty, price, line in valid_items
            ])
            Receipt.objects.create(transaction=record)
        messages.success(request, f"Transaction {receipt_number} recorded.")
        return redirect("receipt_detail", pk=record.pk)
    return render(request, "transactions/transaction_form.html", {"payment_choices": Transaction.PAYMENT_CHOICES})


@login_required(login_url="login")
def receipt_detail(request, pk):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    record = get_object_or_404(
        Transaction.objects.select_related("business", "customer", "recorded_by").prefetch_related("items"),
        pk=pk, business=membership.business,
    )
    return render(request, "transactions/receipt_detail.html", {"record": record})


@login_required(login_url="login")
@require_POST
def receipt_printed(request, pk):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    record = get_object_or_404(Transaction, pk=pk, business=membership.business)
    receipt, _ = Receipt.objects.get_or_create(transaction=record)
    Receipt.objects.filter(pk=receipt.pk).update(print_count=F("print_count") + 1)
    return redirect("receipt_detail", pk=record.pk)


@login_required(login_url="login")
@require_POST
def transaction_cancel(request, pk):
    membership = _membership_for(request.user)
    if not membership:
        return redirect("business_setup")
    record = get_object_or_404(Transaction, pk=pk, business=membership.business)
    reason = request.POST.get("cancellation_reason", "").strip()
    if record.status == "CANCELLED":
        messages.info(request, "This transaction has already been cancelled.")
    elif len(reason) < 5:
        messages.error(request, "Provide a cancellation reason of at least five characters.")
    else:
        record.status = "CANCELLED"
        record.cancellation_reason = reason
        record.cancelled_by = request.user
        record.cancelled_at = timezone.now()
        record.save(update_fields=["status", "cancellation_reason", "cancelled_by", "cancelled_at"])
        messages.success(request, "Transaction cancelled. The original record has been retained.")
    return redirect("receipt_detail", pk=record.pk)


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("home")
