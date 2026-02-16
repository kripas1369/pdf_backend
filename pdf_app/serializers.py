# pdf_app/serializers.py - COMPLETE SERIALIZERS

from decimal import Decimal
from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

# ============================================
# AUTHENTICATION SERIALIZERS
# ============================================

def _validate_phone(value):
    """Normalize and validate phone number"""
    phone = value.strip().replace(' ', '').replace('-', '')
    if not phone.startswith('+977'):
        phone = '+977' + phone.lstrip('0')
    if len(phone) < 14:
        raise serializers.ValidationError("Invalid phone number format")
    return phone


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=6, write_only=True)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    referral_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_phone(self, value):
        phone = _validate_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Phone number already registered")
        return phone


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    
    def validate_phone(self, value):
        return _validate_phone(value)


class SendOTPSerializer(serializers.Serializer):
    """For forgot-password: send OTP only if user exists"""
    phone = serializers.CharField(max_length=15)
    
    def validate_phone(self, value):
        return _validate_phone(value)


class ForgotPasswordResetSerializer(serializers.Serializer):
    """Verify OTP and set new password"""
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=6, write_only=True)
    
    def validate_phone(self, value):
        return _validate_phone(value)


class UserSerializer(serializers.ModelSerializer):
    has_profile = serializers.SerializerMethodField()
    subscription_tier = serializers.SerializerMethodField()
    messages_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'referral_code',
            'pdf_views_count', 'days_since_install',
            'has_profile', 'subscription_tier', 'messages_remaining',
            'created_at'
        ]
        read_only_fields = ['id', 'referral_code', 'created_at']
    
    def get_has_profile(self, obj):
        return hasattr(obj, 'student_profile')
    
    def get_subscription_tier(self, obj):
        try:
            return obj.subscription.tier
        except:
            return 'FREE'
    
    def get_messages_remaining(self, obj):
        try:
            return obj.message_quota.get_remaining()
        except:
            return 2  # Default FREE tier


# ============================================
# PDF SERIALIZERS (UPDATED)
# ============================================

class PDFFileSerializer(serializers.ModelSerializer):
    """PDF list/detail with has_access and is_locked for app (free / purchased / subscription)."""
    is_locked = serializers.SerializerMethodField()
    has_access = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()

    class Meta:
        model = PDFFile
        fields = [
            'id', 'title', 'subtitle', 'year', 'file',
            'pdf_type', 'is_solution', 'is_premium', 'price',
            'is_locked', 'has_access'
        ]

    def get_is_premium(self, obj):
        """Solution and Question+Solution PDFs are always premium."""
        if obj.pdf_type in ('SOLUTION', 'BOTH') or obj.is_solution:
            return True
        return obj.is_premium

    def get_price(self, obj):
        """Solution / Question+Solution PDFs are always Rs 15; others use stored price."""
        if obj.pdf_type in ('SOLUTION', 'BOTH') or obj.is_solution:
            return Decimal('15.00')
        return obj.price

    def _user_has_access(self, obj):
        """
        True if: PDF is free, OR user has active subscription (GOLD/DIAMOND),
        OR user purchased this PDF, OR user owns a package that covers this PDF.
        Used for both has_access and is_locked. Requires request in context.
        """
        # 1. Free PDF (not premium and not solution) -> always has access
        if not obj.is_premium and not obj.is_solution:
            return True

        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user = request.user

        # 2. Active subscription (Gold/Diamond, not expired, is_active)
        try:
            sub = user.subscription
            if (
                sub.is_active
                and sub.tier in ('GOLD', 'DIAMOND')
                and not sub.is_expired()
            ):
                return True
        except Subscription.DoesNotExist:
            pass

        # 3. User purchased this PDF (PdfAccess exists; payment was approved when created)
        if PdfAccess.objects.filter(user=user, pdf=obj).exists():
            return True

        # 4. Package access – check if any approved package covers this PDF.
        #    For list views, 'package_pdf_ids' is pre-computed (efficient).
        #    For single-object contexts (bookmarks, etc.) fall back to per-PDF check.
        package_pdf_ids = self.context.get('package_pdf_ids')
        if package_pdf_ids is not None:
            if obj.id in package_pdf_ids:
                return True
        else:
            from .utils import get_user_active_packages, pdf_covered_by_package
            for pkg in get_user_active_packages(user):
                if pdf_covered_by_package(obj, pkg):
                    return True

        return False

    def get_has_access(self, obj):
        return self._user_has_access(obj)

    def get_is_locked(self, obj):
        # Premium/solution PDFs are locked when user does not have access
        return not self._user_has_access(obj)


# ============================================
# STUDENT PDF UPLOAD (free PDFs, admin approval)
# ============================================

class StudentPDFUploadSerializer(serializers.ModelSerializer):
    """Student uploads a free (question) PDF; admin must approve before it shows in app."""
    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
    ALLOWED_EXTENSIONS = ('pdf',)

    class Meta:
        model = PDFFile
        fields = ['title', 'subtitle', 'year', 'subject', 'file']

    def validate_subject(self, value):
        if not value:
            raise serializers.ValidationError('Subject is required.')
        return value

    def validate_year(self, value):
        if value is None:
            raise serializers.ValidationError('Year is required.')
        # Accept academic years (e.g. 2078, 2081 BS or 2024 AD)
        if value < 1990 or value > 2100:
            raise serializers.ValidationError('Year must be between 1990 and 2100.')
        return value

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError('PDF file is required.')
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError('File size must not exceed 15MB.')
        ext = (value.name or '').split('.')[-1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError('Only PDF files are allowed.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        validated_data['uploaded_by'] = request.user
        validated_data['is_approved'] = False
        validated_data['pdf_type'] = 'QUESTION'
        validated_data['is_premium'] = False
        validated_data['price'] = Decimal('0.00')
        return super().create(validated_data)


class MyPDFUploadSerializer(serializers.ModelSerializer):
    """List student's own uploads (pending/approved)."""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = PDFFile
        fields = ['id', 'title', 'subtitle', 'year', 'subject', 'subject_name', 'file', 'is_approved', 'status', 'created_at']

    def get_status(self, obj):
        return 'approved' if obj.is_approved else 'pending'


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name']


class TopicCreateSerializer(serializers.ModelSerializer):
    """Student creates a new topic; admin must approve before it shows in app."""
    class Meta:
        model = Topic
        fields = ['id', 'name', 'is_approved']
        read_only_fields = ['id', 'is_approved']

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('Name is required.')
        if Topic.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError('A topic with this name already exists.')
        return name

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        validated_data['uploaded_by'] = request.user
        validated_data['is_approved'] = False
        return super().create(validated_data)


class SubjectCreateSerializer(serializers.ModelSerializer):
    """Student creates a new subject under any topic (approved or pending). Admin approves PDF → subject and topic auto-approved."""
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'topic', 'topic_name', 'is_approved']
        read_only_fields = ['id', 'topic_name', 'is_approved']

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('Name is required.')
        if Subject.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError('A subject with this name already exists.')
        return name

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        validated_data['uploaded_by'] = request.user
        validated_data['is_approved'] = False
        return super().create(validated_data)


class SubjectSerializer(serializers.ModelSerializer):
    """Subjects under a topic; has_premium_pdfs so app can show lock icon."""
    has_premium_pdfs = serializers.BooleanField(read_only=True)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'has_premium_pdfs', 'is_locked']

    def get_is_locked(self, obj):
        return getattr(obj, 'has_premium_pdfs', False)


# ============================================
# SUBSCRIPTION SERIALIZERS
# ============================================

class SubscriptionSerializer(serializers.ModelSerializer):
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    message_limit = serializers.IntegerField(source='get_message_limit', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'tier', 'tier_display', 'started_at', 'expires_at',
            'is_active', 'is_expired', 'message_limit', 'days_remaining'
        ]
    
    def get_days_remaining(self, obj):
        if not obj.expires_at:
            return None
        remaining = (obj.expires_at - timezone.now()).days
        return max(0, remaining)


class SubscriptionPlanSerializer(serializers.Serializer):
    """Available subscription plans"""
    tier = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    duration_days = serializers.IntegerField()
    features = serializers.ListField(child=serializers.CharField())
    message_limit = serializers.IntegerField()


# ============================================
# PAYMENT SERIALIZERS (QR SYSTEM)
# ============================================

class PaymentCreateSerializer(serializers.ModelSerializer):
    """POST /api/payment/create/ - multipart/form-data; SINGLE_PDF / packages / SUBSCRIPTION."""
    payment_type = serializers.ChoiceField(
        choices=[
            ('SUBSCRIPTION', 'Subscription (all premium)'),
            ('SINGLE_PDF', 'Single PDF'),
            ('SUBJECT_PACKAGE', 'Subject-wise package'),
            ('TOPIC_PACKAGE', 'Topic package – all subjects in one topic'),
            ('YEAR_PACKAGE', 'Single year package'),
            ('FULL_PACKAGE', 'Full package (all years 1–4)'),
        ]
    )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(max_length=50)
    transaction_note = serializers.CharField(required=False, allow_blank=True)
    tier = serializers.CharField(max_length=20, required=False, allow_blank=True)
    purchased_pdf = serializers.PrimaryKeyRelatedField(
        queryset=PDFFile.objects.all(), required=False, allow_null=True
    )
    purchased_package = serializers.PrimaryKeyRelatedField(
        queryset=PDFPackage.objects.filter(is_active=True), required=False, allow_null=True
    )

    class Meta:
        model = Payment
        fields = [
            'payment_type', 'amount', 'tier',
            'screenshot', 'payment_method', 'transaction_note',
            'purchased_pdf', 'purchased_package'
        ]

    def validate_screenshot(self, value):
        if not value:
            raise serializers.ValidationError("Screenshot is required.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Screenshot must be less than 5MB")
        return value

    def validate(self, attrs):
        payment_type = attrs.get('payment_type')
        if payment_type == 'SINGLE_PDF':
            if not attrs.get('purchased_pdf'):
                raise serializers.ValidationError({
                    'purchased_pdf': 'This field is required when payment_type is SINGLE_PDF.'
                })
            attrs['tier'] = None
            attrs['purchased_package'] = None
        elif payment_type in ('SUBJECT_PACKAGE', 'TOPIC_PACKAGE', 'YEAR_PACKAGE', 'FULL_PACKAGE'):
            if not attrs.get('purchased_package'):
                raise serializers.ValidationError({
                    'purchased_package': 'This field is required when payment_type is SUBJECT_PACKAGE, TOPIC_PACKAGE, YEAR_PACKAGE, or FULL_PACKAGE.'
                })
            pkg = attrs['purchased_package']
            type_map = {'SUBJECT_PACKAGE': 'SUBJECT', 'TOPIC_PACKAGE': 'TOPIC', 'YEAR_PACKAGE': 'YEAR', 'FULL_PACKAGE': 'ALL_YEARS'}
            if pkg.package_type != type_map.get(payment_type):
                raise serializers.ValidationError({
                    'purchased_package': f'Package type must match: use a {payment_type.replace("_", " ").title()} package.'
                })
            attrs['tier'] = None
            attrs['purchased_pdf'] = None
        elif payment_type == 'SUBSCRIPTION':
            tier = (attrs.get('tier') or '').strip()
            if not tier:
                raise serializers.ValidationError({
                    'tier': 'This field is required when payment_type is SUBSCRIPTION.'
                })
            tier_upper = tier.upper()
            if tier_upper not in ('GOLD', 'DIAMOND'):
                if tier_upper in ('PLATINUM',):
                    tier_upper = 'DIAMOND'
                else:
                    raise serializers.ValidationError({
                        'tier': 'Must be one of: GOLD, DIAMOND (or gold, platinum).'
                    })
            attrs['tier'] = tier_upper
            attrs['purchased_pdf'] = None
            attrs['purchased_package'] = None
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        return Payment.objects.create(user=user, **validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    purchased_package_name = serializers.CharField(source='purchased_package.name', read_only=True, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'user_phone', 'payment_type', 'amount',
            'tier', 'tier_display', 'purchased_pdf', 'purchased_package', 'purchased_package_name',
            'screenshot', 'payment_method', 'transaction_note', 'status', 'status_display',
            'admin_notes', 'created_at', 'verified_at'
        ]
        read_only_fields = ['id', 'payment_id', 'status', 'verified_at']


class PaymentVerifySerializer(serializers.Serializer):
    """Admin uses this to approve/reject payments"""
    payment_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    admin_notes = serializers.CharField(required=False, allow_blank=True)


class PDFPackageListSerializer(serializers.ModelSerializer):
    """For GET /api/subscription/packages/ - list packages for app."""
    package_type_display = serializers.CharField(source='get_package_type_display', read_only=True)
    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)
    action = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    pdf_count = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    topic_name = serializers.SerializerMethodField()

    class Meta:
        model = PDFPackage
        fields = [
            'id', 'name', 'package_type', 'package_type_display',
            'content_type', 'content_type_display',
            'action', 'description',
            'topic', 'topic_name', 'subject', 'subject_name',
            'year', 'price', 'pdf_count', 'is_solution_package',
        ]

    def get_action(self, obj):
        """The payment_type value Flutter must send in POST /api/payment/create/."""
        mapping = {
            'SUBJECT': 'SUBJECT_PACKAGE',
            'TOPIC': 'TOPIC_PACKAGE',
            'YEAR': 'YEAR_PACKAGE',
            'ALL_YEARS': 'FULL_PACKAGE',
        }
        return mapping.get(obj.package_type, 'FULL_PACKAGE')

    def get_description(self, obj):
        """Ready-made subtitle for the app to display."""
        parts = []
        if obj.subject_id:
            parts.append(obj.subject.name)
        elif obj.topic_id:
            parts.append(obj.topic.name)
        if obj.year:
            parts.append(str(obj.year))
        parts.append(obj.get_content_type_display())
        parts.append(f'{obj.pdfs.count()} PDFs')
        return ' \u2022 '.join(parts)  # e.g. "Physics \u2022 2081 \u2022 All PDFs \u2022 24 PDFs"

    def get_pdf_count(self, obj):
        return obj.pdfs.count()

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject_id else None

    def get_topic_name(self, obj):
        return obj.topic.name if obj.topic_id else None


# ============================================
# COLLEGE & STUDENT SERIALIZERS
# ============================================

class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ['id', 'name', 'name_nepali', 'location', 'district', 'total_students', 'rank']


class StudentProfileSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.name', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'college', 'college_name', 'program', 'year', 'section',
            'verification_status', 'verification_status_display',
            'verification_photo', 'verified_at'
        ]
        read_only_fields = ['verification_status', 'verified_at']


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ['college', 'program', 'year', 'section', 'verification_photo']
    
    def create(self, validated_data):
        user = self.context['request'].user
        profile, created = StudentProfile.objects.update_or_create(
            user=user,
            defaults=validated_data
        )
        return profile


# ============================================
# CHAT SERIALIZERS
# ============================================

class StudyGroupSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudyGroup
        fields = [
            'id', 'college', 'college_name', 'group_type',
            'program', 'year', 'name', 'member_count',
            'total_messages'
        ]
    
    def get_member_count(self, obj):
        return obj.members.count()


class GroupMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_phone = serializers.CharField(source='sender.phone', read_only=True)
    pdf_title = serializers.CharField(source='pdf_file.title', read_only=True)
    
    class Meta:
        model = GroupMessage
        fields = [
            'id', 'sender', 'sender_name', 'sender_phone',
            'message', 'pdf_file', 'pdf_title',
            'created_at', 'is_deleted'
        ]
        read_only_fields = ['sender', 'created_at']


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200)
    pdf_file = serializers.PrimaryKeyRelatedField(
        queryset=PDFFile.objects.all(),
        required=False,
        allow_null=True
    )
    
    def validate_message(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


# ============================================
# REFERRAL SERIALIZERS
# ============================================

class ReferralSerializer(serializers.ModelSerializer):
    referrer_name = serializers.CharField(source='referrer.name', read_only=True)
    referred_name = serializers.CharField(source='referred.name', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'referrer', 'referrer_name',
            'referred', 'referred_name',
            'code_used', 'status', 'created_at'
        ]


class ReferralStatsSerializer(serializers.Serializer):
    total_referrals = serializers.IntegerField()
    completed_referrals = serializers.IntegerField()
    pending_referrals = serializers.IntegerField()
    total_rewards = serializers.IntegerField()
    next_reward_at = serializers.IntegerField()


class ReferralRewardSerializer(serializers.ModelSerializer):
    reward_display = serializers.CharField(source='get_reward_type_display', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = ReferralReward
        fields = ['reward_type', 'reward_display', 'expires_at', 'is_active', 'days_remaining', 'granted_at']
    
    def get_days_remaining(self, obj):
        if not obj.is_active:
            return 0
        remaining = (obj.expires_at - timezone.now()).days
        return max(0, remaining)


# ============================================
# STREAK SERIALIZERS
# ============================================

class UserStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStreak
        fields = [
            'current_streak', 'longest_streak',
            'last_activity_date', 'total_days_active',
            'streak_frozen'
        ]


# ============================================
# BOOKMARK SERIALIZERS
# ============================================

class UserBookmarkSerializer(serializers.ModelSerializer):
    pdf = PDFFileSerializer(read_only=True)
    pdf_id = serializers.PrimaryKeyRelatedField(
        queryset=PDFFile.objects.all(),
        source='pdf',
        write_only=True
    )
    
    class Meta:
        model = UserBookmark
        fields = ['id', 'pdf', 'pdf_id', 'created_at']
        read_only_fields = ['created_at']


# ============================================
# ANALYTICS SERIALIZERS
# ============================================

class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = ['date', 'pdfs_viewed', 'messages_sent', 'time_spent_minutes']


class UsageLogSerializer(serializers.Serializer):
    """POST /api/usage/log/ - report app usage from Flutter."""
    time_spent_minutes = serializers.IntegerField(min_value=0, max_value=1440, default=0, help_text='Minutes spent in app in this session')
    time_spent_seconds = serializers.IntegerField(min_value=0, max_value=86400, required=False, help_text='Alternative: seconds spent (converted to minutes)')
    pdfs_viewed = serializers.IntegerField(min_value=0, max_value=1000, default=0, help_text='Optional: number of PDFs viewed in this session to add')

    def validate(self, data):
        if data.get('time_spent_minutes', 0) == 0 and data.get('time_spent_seconds', 0) == 0 and data.get('pdfs_viewed', 0) == 0:
            raise serializers.ValidationError('Send at least one of time_spent_minutes, time_spent_seconds, or pdfs_viewed.')
        return data


# ============================================
# FEEDBACK & QUERY (KEEP EXISTING)
# ============================================

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'name', 'description', 'created_at']


class UserQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserQuery
        fields = ['id', 'name', 'email', 'topic', 'submitted_at']
        read_only_fields = ['submitted_at']


# ============================================
# LEADERBOARD SERIALIZERS
# ============================================

class CollegeLeaderboardSerializer(serializers.ModelSerializer):
    rank_change = serializers.IntegerField(default=0)  # Calculate rank movement
    
    class Meta:
        model = College
        fields = [
            'id', 'name', 'name_nepali', 'location',
            'total_students', 'rank', 'rank_change'
        ]


# ============================================
# NOTIFICATION SERIALIZERS
# ============================================

class NotificationSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'subject', 'subject_name',
            'action_url', 'is_read', 'is_pinned', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject else None


class NotificationUpdateSerializer(serializers.Serializer):
    """PATCH: mark read and/or pin (save for later)."""
    is_read = serializers.BooleanField(required=False)
    is_pinned = serializers.BooleanField(required=False)


# ============================================
# SUBJECT ROUTINE SERIALIZERS
# ============================================

class SubjectRoutineSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    user_has_reminder = serializers.SerializerMethodField()

    class Meta:
        model = SubjectRoutine
        fields = [
            'id', 'subject', 'subject_name', 'day_of_week', 'day_display',
            'start_time', 'end_time', 'title', 'description', 'order',
            'user_has_reminder',
        ]

    def get_user_has_reminder(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.reminder_users.filter(user=request.user).exists()


class UserRoutineReminderSerializer(serializers.ModelSerializer):
    routine = SubjectRoutineSerializer(read_only=True)
    routine_id = serializers.PrimaryKeyRelatedField(
        queryset=SubjectRoutine.objects.all(),
        source='routine',
        write_only=True,
    )

    class Meta:
        model = UserRoutineReminder
        fields = ['id', 'routine', 'routine_id', 'notify_minutes_before', 'created_at']
        read_only_fields = ['id', 'created_at']


# ============================================
# FEED POST (image, title, description; user can like)
# ============================================

class FeedPostSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'image', 'image_url', 'title', 'description',
            'like_count', 'is_liked', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_like_count(self, obj):
        return getattr(obj, '_like_count', obj.likes.count())

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return getattr(obj, '_is_liked', obj.likes.filter(user=request.user).exists())