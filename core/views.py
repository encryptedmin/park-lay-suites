from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User, Room, Booking, GCashAccount
from .forms import CustomerRegistrationForm, CustomerProfileForm, RoomForm, OnlineBookingForm, WalkInBookingForm, GCashAccountForm, BookingUpdateForm

def calculate_available_rooms(room, check_in_date, check_out_date, exclude_booking_id=None):
    overlapping_bookings = Booking.objects.filter(
        room=room,
        status='Confirmed',
        check_in__lt=check_out_date,
        check_out__gt=check_in_date
    )
    if exclude_booking_id:
        overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking_id)
    return room.total_quantity - overlapping_bookings.count()

def calculate_booking_total(room, check_in_date, check_out_date):
    delta = check_out_date - check_in_date
    nights = delta.days if delta.days > 0 else 1
    return room.price * nights

def customer_queryset():
    return User.objects.filter(is_customer=True, is_employee=False).order_by('last_name', 'first_name', 'username')

# --- AUTHENTICATION ---
def register_view(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_customer = True
            user.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome.")
            return redirect('customer_home')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            if user.is_employee:
                return redirect('employee_dashboard')
            return redirect('customer_home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form, 'next': next_url})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')

# --- CUSTOMER FACE ---
def customer_home(request):
    rooms = Room.objects.all()
    confirmed_bookings = Booking.objects.filter(status='Confirmed')
    room_data = [
        {
            'id': room.id,
            'name': room.name,
            'price': float(room.price),
            'total_quantity': room.total_quantity,
        }
        for room in rooms
    ]
    confirmed_bookings_data = [
        {
            'room_id': booking.room_id,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
        }
        for booking in confirmed_bookings
    ]
    return render(request, 'core/customer_home.html', {
        'rooms': rooms,
        'room_data': room_data,
        'confirmed_bookings_data': confirmed_bookings_data,
    })

@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    gcash_accounts = GCashAccount.objects.all().order_by('-created_at')

    # Get all confirmed bookings for this room for availability calculation
    confirmed_bookings = Booking.objects.filter(room=room, status='Confirmed')
    confirmed_bookings_data = [
        {
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
        }
        for booking in confirmed_bookings
    ]

    if request.method == 'POST':
        form = OnlineBookingForm(request.POST, request.FILES)
        if form.is_valid():
            booking = form.save(commit=False)
            available = calculate_available_rooms(room, booking.check_in, booking.check_out)
            if available > 0:
                booking.customer = request.user
                booking.guest_name = f"{request.user.first_name} {request.user.last_name}"
                booking.room = room
                booking.booking_type = 'Online'
                
                booking.total_price = calculate_booking_total(room, booking.check_in, booking.check_out)
                
                booking.save()
                messages.success(request, "Booking submitted successfully! Waiting for verification.")
                return redirect('customer_dashboard')
            else:
                form.add_error(None, 'Room is not available for these dates.')
    else:
        form = OnlineBookingForm(initial={
            'check_in': request.GET.get('check_in') or None,
            'check_out': request.GET.get('check_out') or None,
        })
    return render(request, 'core/book_room.html', {
        'form': form,
        'room': room,
        'gcash_accounts': gcash_accounts,
        'confirmed_bookings_data': confirmed_bookings_data,
    })

@login_required
def customer_dashboard(request):
    bookings = Booking.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'core/customer_dashboard.html', {'bookings': bookings})

# --- EMPLOYEE FACE ---
@login_required
def employee_dashboard(request):
    if not request.user.is_employee: return redirect('customer_home')
    
    pending_bookings = Booking.objects.filter(status='Pending').order_by('created_at')
    confirmed_bookings = Booking.objects.filter(status='Confirmed').order_by('created_at')
    closed_bookings = Booking.objects.filter(status__in=['Rejected', 'Cancelled']).order_by('-created_at')[:20]
    rooms = Room.objects.all()
    gcash_accounts = GCashAccount.objects.all().order_by('-created_at')
    customers = customer_queryset()
    return render(request, 'core/employee_dashboard.html', {
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'closed_bookings': closed_bookings,
        'rooms': rooms,
        'gcash_accounts': gcash_accounts,
        'customers': customers,
    })

@login_required
def confirm_booking(request, booking_id):
    if not request.user.is_employee: return redirect('customer_home')
    booking = get_object_or_404(Booking, id=booking_id)
    available = calculate_available_rooms(booking.room, booking.check_in, booking.check_out, exclude_booking_id=booking.id)
    if available <= 0:
        messages.error(request, f"{booking.room.name} is no longer available for those dates.")
        return redirect('employee_dashboard')
    booking.status = 'Confirmed'
    booking.save()
    messages.success(request, f"Booking for {booking.guest_name} has been confirmed.")
    return redirect('employee_dashboard')

@login_required
def reject_booking(request, booking_id):
    if not request.user.is_employee: return redirect('customer_home')
    booking = get_object_or_404(Booking, id=booking_id)
    booking.status = 'Rejected'
    booking.save()
    messages.warning(request, f"Booking for {booking.guest_name} has been rejected.")
    return redirect('employee_dashboard')

@login_required
def manage_customers(request):
    if not request.user.is_employee: return redirect('customer_home')
    customers = customer_queryset()
    return render(request, 'core/customer_management.html', {'customers': customers})

@login_required
def add_customer(request):
    if not request.user.is_employee: return redirect('customer_home')
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer profile added successfully.")
            return redirect('manage_customers')
    else:
        form = CustomerProfileForm()
    return render(request, 'core/customer_profile_form.html', {
        'form': form,
        'title': 'Add customer profile',
        'button_label': 'Save Customer',
    })

@login_required
def edit_customer(request, customer_id):
    if not request.user.is_employee: return redirect('customer_home')
    customer = get_object_or_404(customer_queryset(), id=customer_id)
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer profile updated successfully.")
            return redirect('manage_customers')
    else:
        form = CustomerProfileForm(instance=customer)
    return render(request, 'core/customer_profile_form.html', {
        'form': form,
        'customer': customer,
        'title': f'Edit customer: {customer.username}',
        'button_label': 'Update Customer',
    })

@login_required
def delete_customer(request, customer_id):
    if not request.user.is_employee: return redirect('customer_home')
    customer = get_object_or_404(customer_queryset(), id=customer_id)
    if request.method == 'POST':
        customer.delete()
        messages.warning(request, "Customer profile deleted.")
    return redirect('manage_customers')

def user_can_manage_booking(user, booking):
    if user.is_employee:
        return True
    return booking.customer_id == user.id and booking.status in ['Pending', 'Confirmed']

def booking_return_url(user):
    return 'employee_dashboard' if user.is_employee else 'customer_dashboard'

@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if not user_can_manage_booking(request.user, booking):
        messages.error(request, "You do not have permission to modify that booking.")
        return redirect(booking_return_url(request.user))
    if booking.status in ['Rejected', 'Cancelled']:
        messages.warning(request, "Rejected or cancelled bookings can no longer be modified.")
        return redirect(booking_return_url(request.user))

    if request.method == 'POST':
        form = BookingUpdateForm(request.POST, instance=booking)
        if form.is_valid():
            updated_booking = form.save(commit=False)
            available = calculate_available_rooms(
                updated_booking.room,
                updated_booking.check_in,
                updated_booking.check_out,
                exclude_booking_id=booking.id,
            )
            if available > 0:
                old_total = booking.total_price
                updated_booking.total_price = calculate_booking_total(
                    updated_booking.room,
                    updated_booking.check_in,
                    updated_booking.check_out,
                )
                updated_booking.save()
                if updated_booking.total_price < old_total:
                    messages.warning(request, "Booking updated. Paid transactions are final and non-refundable, so any lower total is not refunded.")
                else:
                    messages.success(request, "Booking updated successfully. Paid transactions remain final and non-refundable.")
                return redirect(booking_return_url(request.user))
            form.add_error(None, 'Room is not available for these dates.')
    else:
        form = BookingUpdateForm(instance=booking)

    return render(request, 'core/booking_update_form.html', {
        'form': form,
        'booking': booking,
        'is_employee_view': request.user.is_employee,
    })

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if not user_can_manage_booking(request.user, booking):
        messages.error(request, "You do not have permission to cancel that booking.")
        return redirect(booking_return_url(request.user))
    if request.method == 'POST':
        if booking.status in ['Rejected', 'Cancelled']:
            messages.warning(request, "This booking is already closed.")
        else:
            booking.status = 'Cancelled'
            booking.save()
            messages.warning(request, "Booking cancelled. All paid transactions are final and non-refundable.")
    return redirect(booking_return_url(request.user))

@login_required
def add_room(request):
    if not request.user.is_employee: return redirect('customer_home')
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Room added successfully!")
            return redirect('employee_dashboard')
    else:
        form = RoomForm()
    return render(request, 'core/add_room.html', {'form': form})

@login_required
def edit_room(request, room_id):
    if not request.user.is_employee: return redirect('customer_home')
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, "Room updated successfully!")
            return redirect('employee_dashboard')
    else:
        form = RoomForm(instance=room)
    return render(request, 'core/edit_room.html', {'form': form, 'room': room})

@login_required
def add_gcash_account(request):
    if not request.user.is_employee: return redirect('customer_home')
    if request.method == 'POST':
        form = GCashAccountForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "GCash account added successfully.")
            return redirect('employee_dashboard')
    else:
        form = GCashAccountForm()
    return render(request, 'core/gcash_account_form.html', {
        'form': form,
        'title': 'Add GCash account',
        'subtitle': 'Upload the QR code and account details customers will use for payment.',
        'button_label': 'Save GCash Account',
    })

@login_required
def edit_gcash_account(request, account_id):
    if not request.user.is_employee: return redirect('customer_home')
    account = get_object_or_404(GCashAccount, id=account_id)
    if request.method == 'POST':
        form = GCashAccountForm(request.POST, request.FILES, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, "GCash account updated successfully.")
            return redirect('employee_dashboard')
    else:
        form = GCashAccountForm(instance=account)
    return render(request, 'core/gcash_account_form.html', {
        'form': form,
        'account': account,
        'title': f'Edit GCash account: {account.account_name}',
        'subtitle': 'Update the QR code, account name, or account number shown to customers.',
        'button_label': 'Update GCash Account',
    })

@login_required
def delete_gcash_account(request, account_id):
    if not request.user.is_employee: return redirect('customer_home')
    account = get_object_or_404(GCashAccount, id=account_id)
    if request.method == 'POST':
        account.delete()
        messages.warning(request, "GCash account deleted.")
    return redirect('employee_dashboard')

@login_required
def walkin_booking(request):
    if not request.user.is_employee: return redirect('customer_home')

    rooms = Room.objects.all()
    confirmed_bookings = Booking.objects.filter(status='Confirmed')
    room_data = [
        {
            'id': room.id,
            'name': room.name,
            'price': float(room.price),
            'total_quantity': room.total_quantity,
            'inclusions': room.inclusions,
            'image_url': room.image.url if room.image else '',
        }
        for room in rooms
    ]
    confirmed_bookings_data = [
        {
            'room_id': booking.room_id,
            'check_in': booking.check_in.isoformat(),
            'check_out': booking.check_out.isoformat(),
        }
        for booking in confirmed_bookings
    ]

    if request.method == 'POST':
        form = WalkInBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            available = calculate_available_rooms(booking.room, booking.check_in, booking.check_out)
            if available > 0:
                booking.booking_type = 'Walk-in'
                booking.status = 'Confirmed'
                
                booking.total_price = calculate_booking_total(booking.room, booking.check_in, booking.check_out)
                
                booking.save()
                messages.success(request, "Walk-in booking confirmed successfully!")
                return redirect('employee_dashboard')
            else:
                form.add_error(None, 'Room unavailable for these dates.')
    else:
        form = WalkInBookingForm()
    return render(request, 'core/walkin_booking.html', {
        'form': form,
        'rooms': rooms,
        'room_data': room_data,
        'confirmed_bookings_data': confirmed_bookings_data,
    })
