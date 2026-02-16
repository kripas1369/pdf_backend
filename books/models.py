from django.db import models
from django.conf import settings


class Book(models.Model):
    CATEGORY_CHOICES = [
        ('ENGINEERING', 'Engineering'),
        ('MEDICAL', 'Medical'),
        ('MANAGEMENT', 'Management'),
        ('LAW', 'Law'),
        ('SCIENCE', 'Science'),
        ('ARTS', 'Arts'),
        ('OTHER', 'Other'),
    ]
    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('LIKE_NEW', 'Like New'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='books',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    front_image = models.ImageField(upload_to='book_images/')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        seller_name = getattr(self.seller, 'name', None) or getattr(self.seller, 'phone', 'Unknown')
        return f"{self.title} - Rs.{self.price} by {seller_name}"


class BookBooking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='book_orders',
    )
    buyer_name = models.CharField(max_length=100)
    buyer_phone = models.CharField(max_length=15)
    buyer_message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['book', 'buyer']]

    def __str__(self):
        return f"{self.buyer_name} → {self.book.title} ({self.status})"
