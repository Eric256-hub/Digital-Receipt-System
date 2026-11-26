from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("business/setup/", views.business_setup, name="business_setup"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/new/", views.transaction_create, name="transaction_create"),
    path("transactions/<int:pk>/", views.receipt_detail, name="receipt_detail"),
    path("transactions/<int:pk>/cancel/", views.transaction_cancel, name="transaction_cancel"),
    path("transactions/<int:pk>/printed/", views.receipt_printed, name="receipt_printed"),
]
