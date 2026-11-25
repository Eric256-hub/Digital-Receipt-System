from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect

from .models import Business, BusinessMembership


def home(request):
    return render(request, 'transactions/home.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Registration completed successfully. Please sign in to continue.'
            )
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'transactions/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'transactions/login.html')


@login_required(login_url='login')
def dashboard(request):
    membership = BusinessMembership.objects.filter(
        user=request.user
    ).select_related('business').first()

    if not membership:
        return redirect('business_setup')

    return render(
        request,
        'transactions/dashboard.html',
        {'business': membership.business}
    )


@login_required(login_url='login')
def business_setup(request):
    membership = BusinessMembership.objects.filter(
        user=request.user
    ).first()

    if membership:
        return redirect('dashboard')

    if request.method == 'POST':
        business_name = request.POST.get('business_name', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        receipt_footer = request.POST.get('receipt_footer', '').strip()

        if not business_name:
            messages.error(request, 'Business name is required.')
        else:
            business = Business.objects.create(
                business_name=business_name,
                address=address,
                phone=phone,
                receipt_footer=receipt_footer
            )

            BusinessMembership.objects.create(
                business=business,
                user=request.user,
                role='ADMIN'
            )

            messages.success(
                request,
                'Business registration completed successfully.'
            )
            return redirect('dashboard')

    return render(request, 'transactions/business_setup.html')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')

    return redirect('login')
