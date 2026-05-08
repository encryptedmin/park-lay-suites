from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_home, name='customer_home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Customer
    path('book/<int:room_id>/', views.book_room, name='book_room'),
    path('my-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('booking/<int:booking_id>/edit/', views.edit_booking, name='edit_booking'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    
    # Employee
    path('admin-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('customers/', views.manage_customers, name='manage_customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    path('add-room/', views.add_room, name='add_room'),
    path('edit-room/<int:room_id>/', views.edit_room, name='edit_room'),
    path('gcash/add/', views.add_gcash_account, name='add_gcash_account'),
    path('gcash/edit/<int:account_id>/', views.edit_gcash_account, name='edit_gcash_account'),
    path('gcash/delete/<int:account_id>/', views.delete_gcash_account, name='delete_gcash_account'),
    path('confirm/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('reject/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('walk-in/', views.walkin_booking, name='walkin_booking'),
]
