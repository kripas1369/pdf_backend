# ========================================
# DJANGO BACKEND - models.py
# ========================================
# Location: pdf_app/models.py
# Copy this entire file to your Django project
# ========================================

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import random
import string
import uuid


# ========================================
# CUSTOM USER MANAGER
# ========================================

class CustomUserManager(BaseUserManager):
    """Custom manager for User model with phone-based authentication"""
    
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, **extra_fields)
        
        if password:
            user.set_password(password)  # Set password if provided
        else:
            user.set_unusable_password()  # Only for OTP-only users
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if password is None:
            # Generate a random password for superuser
            password = ''.join(random.choices(string.digits, k=6))
            print(f"Generated password for superuser {phone}: {password}")
        
        return self.create_user(phone, password=password, **extra_fields)
# ========================================
# USER MODEL (Phone-only authentication)
# ========================================

class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with phone number as primary identifier"""
    
    # Basic Info
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    name = models.CharField(max_length=100, blank=True)
    
    # Gradual Login Tracking
    first_opened_at = models.DateTimeField(null=True, blank=True)
    pdf_views_count = models.IntegerField(default=0)
    days_since_install = models.IntegerField(default=0)
    
    # Referral System
    referral_code = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    
    # Blue tick verification (paid purchase or admin-granted)
    is_verified = models.BooleanField(
        default=False,
        help_text='Verified account (blue tick). Set automatically when user buys any paid package, or manually by admin.'
    )
    
    # Django Auth Fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Updated by app heartbeat; used for active-online count.',
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    def save(self, *args, **kwargs):
        # Auto-generate referral code
        if not self.referral_code:
            self.referral_code = f"SATHI{self.phone[-6:]}{random.randint(10, 99)}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.phone
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['referral_code']),
            models.Index(fields=['last_seen']),
        ]


# ========================================
# OTP MODEL (WhatsApp OTP)
# ========================================

class OTP(models.Model):
    """OTP for phone verification via WhatsApp"""
    
    phone = models.CharField(max_length=15, db_index=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and timezone.now() < self.expires_at and self.attempts < 3
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.phone} - {self.otp}"


# ========================================
# EXISTING PDF MODELS (Keep these)
# ========================================

class Topic(models.Model):
    """Academic topics (TU, PU, etc.). Students can suggest new topics; admin approves."""
    
    name = models.CharField(max_length=100, unique=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_topics',
    )
    is_approved = models.BooleanField(default=True, help_text='False = pending (student-created). Only approved show in app.')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Subject(models.Model):
    """Subjects under each topic. Students can suggest new subjects; admin approves."""
    
    name = models.CharField(max_length=100, unique=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subjects')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_subjects',
    )
    is_approved = models.BooleanField(default=True, help_text='False = pending (student-created). Only approved show in app.')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.topic.name} - {self.name}"

    class Meta:
        ordering = ['topic', 'name']


class PDFFile(models.Model):
    """PDF files (questions, solutions, or both)"""
    
    PDF_TYPE_CHOICES = [
        ('QUESTION', 'Question'),
        ('SOLUTION', 'Solution'),
        ('BOTH', 'Question + Solution'),
    ]
    
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    year = models.PositiveIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='pdfs')
    file = models.FileField(upload_to='pdfs/')
    
    # Content type – determines which tab(s) the PDF appears in
    pdf_type = models.CharField(
        max_length=20, choices=PDF_TYPE_CHOICES, default='QUESTION',
        help_text='Question = Questions tab only. Solution = Solutions tab only. '
                  'Question + Solution = both tabs, always premium.'
    )
    
    # Derived / overridable flags (auto-set from pdf_type on save)
    is_solution = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Auto-set to Rs 15 for Solution / Question+Solution types.')
    
    # Student upload: only free (QUESTION) PDFs; admin must approve before they appear in app
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_pdfs',
    )
    is_approved = models.BooleanField(
        default=True,
        help_text='False = pending approval (student uploads). Only approved PDFs show in app.',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Derive is_solution, is_premium, price from pdf_type. Student uploads stay free."""
        if self.uploaded_by_id:
            # Student upload: force free question PDF only
            self.pdf_type = 'QUESTION'
            self.is_solution = False
            self.is_premium = False
            self.price = Decimal('0.00')
        elif self.pdf_type in ('SOLUTION', 'BOTH'):
            self.is_solution = True
            self.is_premium = True
            self.price = Decimal('15.00')
        elif self.pdf_type == 'QUESTION':
            self.is_solution = False
            # is_premium and price are left as-is so admin can set premium questions manually
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.year})"
    
    class Meta:
        ordering = ['-year', 'title']


# ========================================
# PDF PACKAGES (Subject-wise / Year package)
# ========================================

class PDFPackage(models.Model):
    """
    Two main package types (simple for admin):
    - SUBJECT: Select subject → package = all PDFs in that subject (all years). Shown when user opens that subject.
    - YEAR: Select year → package = all PDFs in that year (all subjects). Shown when user browses that year.
    - ALL_YEARS: Custom – admin selects PDFs manually (optional).
    Content type: All PDFs, Questions only, or Solutions only.
    """
    PACKAGE_TYPE_CHOICES = [
        ('SUBJECT', 'Subject package – all PDFs in one subject (all years)'),
        ('TOPIC', 'Topic package – all subjects under one topic (all PDFs in that topic)'),
        ('YEAR', 'Year package – all PDFs in one year (all subjects)'),
        ('ALL_YEARS', 'Custom – select PDFs manually (optional)'),
    ]
    CONTENT_TYPE_CHOICES = [
        ('ALL', 'All PDFs (questions + solutions)'),
        ('QUESTIONS', 'Questions only'),
        ('SOLUTIONS', 'Solutions only'),
    ]
    
    name = models.CharField(max_length=255, help_text='e.g. Physics – All years, or TU – All subjects')
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True, related_name='packages',
                               help_text='For Topic package: select the topic (all subjects under it). Leave empty for Subject/Year.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='packages',
                                 help_text='For Subject package: select the subject. Leave empty for Topic/Year package.')
    year = models.PositiveIntegerField(null=True, blank=True,
                                       help_text='For Year package: select the year. Leave empty for Topic/Subject package.')
    content_type = models.CharField(
        max_length=20, choices=CONTENT_TYPE_CHOICES, default='ALL',
        help_text='Include: All PDFs, Questions only, or Solutions only.'
    )
    pdfs = models.ManyToManyField(PDFFile, related_name='packages', blank=True,
                                  help_text='Auto-filled on Save. You can adjust after if needed.')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Package price')
    is_active = models.BooleanField(default=True)
    is_solution_package = models.BooleanField(
        default=False,
        help_text='Set automatically when Content type is Solutions only (used by app API).'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year', 'name']
        verbose_name = 'PDF Package'
        verbose_name_plural = 'PDF Packages'
    
    def save(self, *args, **kwargs):
        self.is_solution_package = (self.content_type == 'SOLUTIONS')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_package_type_display()})"
    
    def pdf_count(self):
        return self.pdfs.count()


class Feedback(models.Model):
    """User feedback"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks',
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.created_at}"


class UserQuery(models.Model):
    """User queries/requests"""
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.name} - {self.topic.name}"


# ========================================
# SUBSCRIPTION MODELS
# ========================================

class Subscription(models.Model):
    """User subscription tiers"""
    
    TIER_CHOICES = [
        ('FREE', 'Bronze (Free)'),
        ('GOLD', 'Gold (₹499/sem)'),
        ('DIAMOND', 'Diamond (₹899/sem)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='FREE')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_subscription')
    
    def is_expired(self):
        """Check if subscription has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def get_message_limit(self):
        """Get daily message limit for tier"""
        limits = {
            'FREE': 2,
            'GOLD': 50,
            'DIAMOND': 999999
        }
        return limits.get(self.tier, 2)
    
    def __str__(self):
        return f"{self.user.phone} - {self.tier}"
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'tier']),
            models.Index(fields=['expires_at']),
        ]


# ========================================
# PAYMENT MODEL (QR Payment System)
# ========================================

class Payment(models.Model):
    """Manual QR payment records"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    TIER_CHOICES = [
        ('GOLD', 'Gold - ₹499/semester'),
        ('DIAMOND', 'Diamond - ₹899/semester'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('SUBSCRIPTION', 'Subscription (all premium PDFs)'),
        ('SINGLE_PDF', 'Single PDF'),
        ('SUBJECT_PACKAGE', 'Subject package – one subject, all PDFs'),
        ('TOPIC_PACKAGE', 'Topic package – all subjects in one topic, all PDFs'),
        ('YEAR_PACKAGE', 'Single year package'),
        ('FULL_PACKAGE', 'Full package (all years 1–4 in one)'),
    ]
    
    # Payment Info
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='SUBSCRIPTION')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, null=True, blank=True)
    
    # Screenshot Upload
    screenshot = models.ImageField(upload_to='payment_screenshots/')
    payment_method = models.CharField(max_length=50, blank=True)  # eSewa, Khalti, Bank
    transaction_note = models.TextField(blank=True)
    
    # Verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    # PDF Purchase (if buying individual PDF)
    purchased_pdf = models.ForeignKey(PDFFile, on_delete=models.SET_NULL, null=True, blank=True)
    # Package purchase (Subject-wise or Year package)
    purchased_package = models.ForeignKey('PDFPackage', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.phone} - ₹{self.amount} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_id']),
        ]


class PaymentQR(models.Model):
    """Payment QR code - Admin uploads one QR image for users to scan (eSewa, Khalti, etc.)"""
    
    qr_image = models.ImageField(upload_to='payment_qr/', help_text='QR code for payment - users scan this')
    instructions = models.CharField(max_length=255, blank=True, help_text='e.g. Scan with eSewa, Khalti')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment QR Code'
        verbose_name_plural = 'Payment QR Code'
    
    def __str__(self):
        return 'Payment QR' if self.qr_image else 'No QR uploaded'
    
    @classmethod
    def get_active(cls):
        """Get the active QR (singleton - use first active)"""
        return cls.objects.filter(is_active=True).first()


class PdfAccess(models.Model):
    """Track which PDFs user has purchased/unlocked"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pdf_accesses')
    pdf = models.ForeignKey(PDFFile, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'pdf']
        indexes = [
            models.Index(fields=['user', 'pdf']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.pdf.title}"


class MessageQuota(models.Model):
    """Track daily message quota for users"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='message_quota')
    messages_sent_today = models.IntegerField(default=0)
    last_reset_date = models.DateField(auto_now_add=True)
    
    def check_can_send(self):
        """Check if user can send message (with auto-reset)"""
        today = timezone.now().date()
        
        # Auto-reset daily quota
        if self.last_reset_date < today:
            self.messages_sent_today = 0
            self.last_reset_date = today
            self.save()
        
        # Get limit from subscription
        try:
            subscription = self.user.subscription
            limit = subscription.get_message_limit()
        except Subscription.DoesNotExist:
            limit = 2  # FREE tier default
        
        return self.messages_sent_today < limit
    
    def increment(self):
        """Increment message count"""
        self.messages_sent_today += 1
        self.save()
    
    def get_remaining(self):
        """Get remaining messages for today"""
        try:
            subscription = self.user.subscription
            limit = subscription.get_message_limit()
        except Subscription.DoesNotExist:
            limit = 2
        
        return max(0, limit - self.messages_sent_today)
    
    def __str__(self):
        return f"{self.user.phone} - {self.messages_sent_today} sent"


# ========================================
# COLLEGE & साथी MODELS
# ========================================

class College(models.Model):
    """Colleges for साथी network"""
    
    name = models.CharField(max_length=200)
    name_nepali = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    total_students = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def update_stats(self):
        """Update student count and rank"""
        self.total_students = self.students.filter(verification_status='APPROVED').count()
        self.save()
    
    def __str__(self):
        return f"{self.name} - {self.location}"
    
    class Meta:
        ordering = ['-total_students', 'name']


class StudentProfile(models.Model):
    """Student verification for साथी"""
    
    PROGRAM_CHOICES = [
        ('BBS', 'BBS'),
        ('BCA', 'BCA'),
        ('BA', 'BA'),
        ('BSW', 'BSW'),
        ('BED', 'BED'),
        ('BSc', 'BSc'),
        ('OTHER', 'Other'),
    ]
    
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES, blank=True)
    year = models.IntegerField(choices=[(1,'1st'),(2,'2nd'),(3,'3rd'),(4,'4th')], null=True, blank=True)
    section = models.CharField(max_length=5, blank=True)
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='PENDING')
    verification_photo = models.ImageField(upload_to='verification/', blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['college', 'program', 'year']),
            models.Index(fields=['verification_status']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.college.name if self.college else 'No College'}"


class StudyGroup(models.Model):
    """Auto-created study groups"""
    
    GROUP_TYPE_CHOICES = [
        ('COLLEGE', 'College'),
        ('PROGRAM', 'Program'),
        ('YEAR', 'Year'),
    ]
    
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='groups')
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES)
    program = models.CharField(max_length=20, blank=True)
    year = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(User, related_name='study_groups')
    total_messages = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.college.name} - {self.name}"
    
    class Meta:
        indexes = [
            models.Index(fields=['college', 'group_type']),
        ]


class GroupMessage(models.Model):
    """Chat messages in study groups"""
    
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=200)
    pdf_file = models.ForeignKey(PDFFile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['group', 'id']),  # For after_id polling
        ]
    
    def __str__(self):
        return f"{self.sender.phone} in {self.group.name}"


# ========================================
# REFERRAL MODELS
# ========================================

class Referral(models.Model):
    """Referral tracking"""
    
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_referrals')
    referred = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_by_user')
    code_used = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[('PENDING','Pending'),('COMPLETED','Completed')], default='PENDING')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['referrer', 'referred']
    
    def __str__(self):
        return f"{self.referrer.phone} → {self.referred.phone}"


class ReferralReward(models.Model):
    """Rewards for referrals"""
    
    REWARD_TYPES = [
        ('AD_FREE_WEEK', '1 Week Ad-Free'),
        ('PREMIUM_FEATURE', 'Premium Feature'),
        ('PREMIUM_MONTH', '1 Month Premium'),
        ('PREMIUM_3MONTH', '3 Months Premium'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rewards')
    reward_type = models.CharField(max_length=30, choices=REWARD_TYPES)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.phone} - {self.get_reward_type_display()}"


# ========================================
# STREAK MODEL
# ========================================

class UserStreak(models.Model):
    """User activity streak"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(auto_now=True)
    total_days_active = models.IntegerField(default=0)
    streak_frozen = models.BooleanField(default=False)  # Premium feature
    
    def log_activity(self):
        """Log daily activity (view PDF or send message)"""
        today = timezone.now().date()
        
        if self.last_activity_date < today:
            days_diff = (today - self.last_activity_date).days
            
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
            elif days_diff > 1 and not self.streak_frozen:
                # Streak broken
                self.current_streak = 1
            # If frozen, don't break streak
            
            self.last_activity_date = today
            self.total_days_active += 1
            
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
            
            self.save()
    
    def __str__(self):
        return f"{self.user.phone} - {self.current_streak} days"


# ========================================
# CLOUD SYNC MODEL
# ========================================

class UserBookmark(models.Model):
    """Cloud-synced bookmarks"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    pdf = models.ForeignKey(PDFFile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'pdf']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.phone} - {self.pdf.title}"


# ========================================
# ANALYTICS MODEL
# ========================================

class UserActivity(models.Model):
    """Daily user activity analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    date = models.DateField(auto_now_add=True)
    pdfs_viewed = models.IntegerField(default=0)
    messages_sent = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.date}"


class UserTopicUsage(models.Model):
    """
    Tracks which topic each user used and how much (per day).
    Used to see which topics are most used in the app and which users use which topics most.
    Flutter app sends topic_usage when logging usage (e.g. when user opens a topic or views PDFs under it).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_usages')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='user_usages')
    date = models.DateField(db_index=True)
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of times user opened/viewed this topic (or PDFs under it) on this day.'
    )
    time_spent_minutes = models.PositiveIntegerField(
        default=0,
        help_text='Optional: minutes spent in this topic on this day.'
    )

    class Meta:
        unique_together = ['user', 'topic', 'date']
        ordering = ['-date', '-usage_count']
        indexes = [
            models.Index(fields=['topic', '-date']),
            models.Index(fields=['user', '-date']),
        ]
        verbose_name = 'User topic usage'
        verbose_name_plural = 'User topic usage'

    def __str__(self):
        return f"{self.user.phone} – {self.topic.name} ({self.date}): {self.usage_count}"


# ========================================
# NOTIFICATIONS (all users; pin / save for later)
# ========================================

class Notification(models.Model):
    """
    In-app notification for a user. Admin can send to one user or "all users"
    (creates one Notification per user). Student can mark read and pin (save for later).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    # Optional: link notification to a subject (e.g. "New PDF in Physics")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    action_url = models.CharField(max_length=500, blank=True, help_text='Optional deep link or URL')
    is_read = models.BooleanField(default=False)
    is_pinned = models.BooleanField(
        default=False,
        help_text='User pinned / saved for later',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'is_pinned']),
        ]

    def __str__(self):
        return f"{self.user.phone} - {self.title[:50]}"


# ========================================
# SUBJECT ROUTINE (per-subject schedule for students)
# ========================================

class SubjectRoutine(models.Model):
    """
    Class routine for a subject (e.g. Physics - Monday 10:00–11:00).
    Students can view routine for each subject. Admin can enable notification
    reminder per routine so user can "start" / subscribe to get notified.
    """
    DAY_CHOICES = [
        (0, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ]
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='routines',
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    title = models.CharField(max_length=200, help_text='e.g. "Unit 1 – Mechanics"')
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text='Order within same day')

    class Meta:
        ordering = ['subject', 'day_of_week', 'order', 'start_time']
        unique_together = ['subject', 'day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['subject', 'day_of_week']),
        ]

    def __str__(self):
        return f"{self.subject.name} – {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class UserRoutineReminder(models.Model):
    """
    User pins/subscribes to a routine slot to get reminder (e.g. "Notify me before Physics class").
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routine_reminders')
    routine = models.ForeignKey(SubjectRoutine, on_delete=models.CASCADE, related_name='reminder_users')
    notify_minutes_before = models.PositiveSmallIntegerField(
        default=15,
        help_text='Send notification this many minutes before start_time',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'routine']
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.phone} – {self.routine}"


# ========================================
# TU NOTICE FEED (Facebook-style: user posts, admin approval, like, bookmark, comment)
# ========================================

class FeedPost(models.Model):
    """
    TU Notice Feed post: image, title, description.
    Users can create posts (status=PENDING); admin approves. Users can like, bookmark, comment.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    image = models.ImageField(upload_to='feed_posts/', blank=True, null=True)  # legacy single image; new posts use FeedPostImage
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tu_notice_posts'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='APPROVED',
        help_text='User-created posts start as Pending; admin approves.'
    )
    is_active = models.BooleanField(default=True, help_text='Inactive posts are hidden from the app')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'status', '-created_at']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.title[:50] if self.title else 'Untitled'


class FeedPostImage(models.Model):
    """Up to 10 images per feed post. Order preserved by 'order' field."""
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='feed_posts/')
    order = models.PositiveSmallIntegerField(default=0, help_text='Display order (0-based).')

    class Meta:
        ordering = ['order']
        indexes = [models.Index(fields=['post'])]

    def __str__(self):
        return f"Image #{self.order} for post #{self.post_id}"


class FeedPostLike(models.Model):
    """User liked a feed post (one like per user per post)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_likes')
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.phone} liked #{self.post_id}"


class FeedPostBookmark(models.Model):
    """User bookmarked a feed post (one bookmark per user per post)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_bookmarks')
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.phone} bookmarked #{self.post_id}"


class FeedPostComment(models.Model):
    """Comment on a feed post."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_comments')
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.phone} on #{self.post_id}: {self.text[:30]}..."