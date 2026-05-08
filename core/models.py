from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_employee = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)

class Room(models.Model):
    name = models.CharField(max_length=100)
    inclusions = models.TextField(help_text="E.g., Free WiFi, AC, TV")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = models.PositiveIntegerField(help_text="Total physical rooms of this type")
    image = models.ImageField(upload_to='rooms/')

    def __str__(self):
        return self.name

class GCashAccount(models.Model):
    account_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=30)
    qr_code = models.ImageField(upload_to='gcash_qr/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    )
    TYPE_CHOICES = (
        ('Online', 'Online'),
        ('Walk-in', 'Walk-in'),
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=150) # Important for walk-ins
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Online')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Payment details
    gcash_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.ImageField(upload_to='payments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.guest_name} - {self.room.name}"

    @property
    def nights(self):
        delta = self.check_out - self.check_in
        return delta.days if delta.days > 0 else 1
