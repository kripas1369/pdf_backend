# pdf_app/views.py - COMPLETE API VIEWS

from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Count, Q, F, Sum, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.conf import settings
from datetime import timedelta
import random

from .models import *
from .serializers import *
from .utils import (
    send_whatsapp_otp, create_auto_groups, update_college_stats,
    grant_subscription_access, grant_package_access, get_pdfs_for_package,
    get_user_active_packages, pdf_covered_by_package,
    get_package_accessible_pdf_ids,
)

User = get_user_model()

# ============================================
# AUTHENTICATION VIEWS
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register with phone + password (no OTP)"""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']
    name = serializer.validated_data.get('name', '').strip()
    referral_code = serializer.validated_data.get('referral_code', '').strip()
    
    user = User.objects.create_user(phone=phone, password=password, name=name or '')
    
    if referral_code:
        referrer = User.objects.filter(referral_code=referral_code).first()
        if referrer:
            user.referred_by = referrer
            user.save()
            Referral.objects.create(
                referrer=referrer,
                referred=user,
                code_used=referral_code
            )
    
    Subscription.objects.create(user=user, tier='FREE')
    MessageQuota.objects.create(user=user)
    UserStreak.objects.create(user=user)
    user.first_opened_at = timezone.now()
    user.save()
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with phone + password (no OTP)"""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']
    
    user = authenticate(request, username=phone, password=password)
    
    if not user:
        return Response({
            'error': 'Invalid phone number or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)
    
    user.last_login = timezone.now()
    user.save()
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    })


# ============================================
# FORGOT PASSWORD (OTP only here)
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_send_otp(request):
    """Send OTP for forgot password (user must exist). OTP printed to terminal until SMS API is configured."""
    serializer = SendOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    
    if not User.objects.filter(phone=phone).exists():
        return Response({
            'error': 'No account found with this phone number'
        }, status=status.HTTP_404_NOT_FOUND)
    
    recent_otps = OTP.objects.filter(
        phone=phone,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    if recent_otps >= 3:
        return Response({
            'error': 'Too many OTP requests. Please try after 1 hour.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    otp_code = OTP.generate_otp()
    
    print("\n" + "="*50)
    print("[OTP] Forgot Password for: %s" % phone)
    print("[OTP] Code: %s" % otp_code)
    print("="*50 + "\n")
    
    OTP.objects.create(phone=phone, otp=otp_code)
    success = send_whatsapp_otp(phone, otp_code)
    
    if not success:
        return Response({
            'error': 'Failed to send OTP. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'message': 'OTP sent successfully',
        'phone': phone
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_reset(request):
    """Verify OTP and set new password"""
    serializer = ForgotPasswordResetSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    otp_entered = serializer.validated_data['otp']
    new_password = serializer.validated_data['new_password']
    
    otp_obj = OTP.objects.filter(
        phone=phone,
        otp=otp_entered,
        is_used=False
    ).order_by('-created_at').first()
    
    if not otp_obj:
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not otp_obj.is_valid():
        return Response({'error': 'OTP expired or already used'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    otp_obj.is_used = True
    otp_obj.save()
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': 'Password reset successfully. You can now login.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get current user info"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user(request):
    """Update user name"""
    user = request.user
    name = request.data.get('name', '').strip()
    
    if name:
        user.name = name
        user.save()
    
    return Response(UserSerializer(user).data)


# ============================================
# QR PAYMENT VIEWS
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def payment_qr(request):
    """Get payment QR code URL - shown in app when user pays (scan QR, then upload screenshot)"""
    qr = PaymentQR.get_active()
    if not qr or not qr.qr_image:
        return Response({
            'qr_url': None,
            'instructions': 'Payment QR not configured. Contact support.'
        })
    
    request_obj = request
    qr_url = request_obj.build_absolute_uri(qr.qr_image.url) if request_obj else qr.qr_image.url
    
    return Response({
        'qr_url': qr_url,
        'instructions': qr.instructions or 'Scan with eSewa, Khalti or your payment app'
    })


class PaymentCreateView(generics.CreateAPIView):
    """
    POST /api/payment/create/
    Content-Type: multipart/form-data
    Authorization: Bearer <access_token>
    Body: screenshot (file), amount, payment_method, payment_type, [tier | purchased_pdf], transaction_note (optional).
    """
    serializer_class = PaymentCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )


class MyPaymentsView(generics.ListAPIView):
    """Get user's payment history"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, payment_id):
    """Check payment status"""
    payment = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    serializer = PaymentSerializer(payment)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def verify_payment(request):
    """Admin approves/rejects payment"""
    serializer = PaymentVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    payment_id = serializer.validated_data['payment_id']
    action = serializer.validated_data['action']
    admin_notes = serializer.validated_data.get('admin_notes', '')
    
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    if action == 'APPROVE':
        payment.status = 'APPROVED'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.admin_notes = admin_notes
        payment.save()
        
        # Grant access based on payment type
        if payment.payment_type == 'SUBSCRIPTION':
            grant_subscription_access(payment)
        elif payment.payment_type == 'SINGLE_PDF' and payment.purchased_pdf:
            PdfAccess.objects.get_or_create(
                user=payment.user,
                pdf=payment.purchased_pdf,
                defaults={'payment': payment}
            )
        else:
            grant_package_access(payment)

        return Response({
            'message': 'Payment approved and access granted',
            'payment': PaymentSerializer(payment).data
        })
    
    elif action == 'REJECT':
        payment.status = 'REJECTED'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.admin_notes = admin_notes
        payment.save()
        
        return Response({
            'message': 'Payment rejected',
            'payment': PaymentSerializer(payment).data
        })


# ============================================
# SUBSCRIPTION VIEWS
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_packages(request):
    """
    Get active PDF packages for the paywall. Pass ?subject_id=X to get packages relevant when user is in that subject:
    - Single PDF: app shows this with the PDF id (not from this API).
    - Subject package: this subject only (all PDFs in subject).
    - Topic package: all subjects in this subject's topic (all PDFs in topic).
    Optional: ?year=Y adds year packages. ?solution_package_only=true for solutions tab.
    """
    from .models import PDFPackage, Subject
    from django.db.models import Q
    packages = PDFPackage.objects.filter(is_active=True).select_related('subject', 'topic').prefetch_related('pdfs')
    subject_id = request.query_params.get('subject_id', '').strip()
    year_param = request.query_params.get('year', '').strip()
    if subject_id and subject_id.isdigit():
        sid = int(subject_id)
        try:
            subject = Subject.objects.get(pk=sid)
            topic_id = subject.topic_id
        except Subject.DoesNotExist:
            topic_id = None
        # Relevant: subject package for this subject OR topic package for this subject's topic
        q = Q(subject_id=sid)  # Subject package
        if topic_id:
            q |= Q(topic_id=topic_id)  # Topic package (all subjects in this topic)
        if year_param and year_param.isdigit():
            y = int(year_param)
            q |= Q(subject_id__isnull=True, topic__isnull=True, year=y)  # Year package
        q |= Q(subject_id__isnull=True, topic__isnull=True, year__isnull=True)  # Full/custom package
        packages = packages.filter(q)
    elif year_param and year_param.isdigit():
        packages = packages.filter(year=int(year_param))
    solution_only = request.query_params.get('solution_package_only', '').strip().lower() == 'true'
    if solution_only:
        packages = packages.filter(is_solution_package=True)
    packages = packages.order_by('package_type', 'name')
    serializer = PDFPackageListSerializer(packages, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_plans(request):
    """Get available subscription plans"""
    plans = [
        {
            'tier': 'FREE',
            'name': 'Bronze (Free)',
            'price': 0,
            'duration_days': 0,
            'features': [
                '2 messages per day',
                'View all PDFs',
                '5 offline downloads',
                '10 bookmarks',
                'Basic features'
            ],
            'message_limit': 2
        },
        {
            'tier': 'GOLD',
            'name': 'Gold',
            'price': 499,
            'duration_days': 180,  # 6 months
            'features': [
                'Access to ALL premium PDFs (all subjects, all years)',
                '50 messages per day',
                'Unlimited offline downloads',
                'Unlimited bookmarks',
                'Model answers included',
                'Ad-free experience',
                'Gold badge on profile'
            ],
            'message_limit': 50
        },
        {
            'tier': 'DIAMOND',
            'name': 'Diamond',
            'price': 899,
            'duration_days': 180,
            'features': [
                'Access to ALL premium PDFs (all subjects, all years)',
                'Unlimited messages',
                'All Gold features',
                'Priority support',
                'Diamond badge',
                'Connect with toppers',
                'Exclusive features'
            ],
            'message_limit': 999999
        }
    ]
    
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscription(request):
    """Get user's subscription details"""
    subscription, created = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'tier': 'FREE'}
    )
    
    serializer = SubscriptionSerializer(subscription)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_pdf_access(request, pdf_id):
    """Check if user has access to PDF (direct purchase, package, or subscription)"""
    pdf = get_object_or_404(PDFFile.objects.select_related('subject'), id=pdf_id)
    
    # Regular PDFs are free (not premium and not solution)
    if not pdf.is_premium and not pdf.is_solution:
        return Response({'has_access': True, 'reason': 'free_pdf'})
    
    user = request.user
    
    # Check subscription
    try:
        subscription = user.subscription
        if subscription.tier in ['GOLD', 'DIAMOND'] and not subscription.is_expired():
            return Response({'has_access': True, 'reason': 'subscription'})
    except:
        pass
    
    # Check individual purchase (includes PdfAccess rows created at package approval time)
    has_purchased = PdfAccess.objects.filter(user=user, pdf=pdf).exists()
    if has_purchased:
        return Response({'has_access': True, 'reason': 'purchased'})
    
    # Check package-level access (covers PDFs added after package approval)
    for pkg in get_user_active_packages(user):
        if pdf_covered_by_package(pdf, pkg):
            # Lazily create PdfAccess so future checks are faster
            PdfAccess.objects.get_or_create(user=user, pdf=pdf)
            return Response({'has_access': True, 'reason': 'package'})
    
    # Locked (premium/solution - requires purchase or subscription). Solution / Both PDFs are always Rs 15.
    price = 15.0 if pdf.pdf_type in ('SOLUTION', 'BOTH') else float(pdf.price)
    return Response({
        'has_access': False,
        'is_premium': True,
        'price': price
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def messages_remaining(request):
    """Get remaining messages for today"""
    quota, created = MessageQuota.objects.get_or_create(user=request.user)
    
    return Response({
        'remaining': quota.get_remaining(),
        'total_today': quota.messages_sent_today,
        'tier': request.user.subscription.tier if hasattr(request.user, 'subscription') else 'FREE'
    })


# ============================================
# COLLEGE & साथी VIEWS
# ============================================

class CollegeListView(generics.ListAPIView):
    """List colleges with search"""
    serializer_class = CollegeSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = College.objects.all()
        search = self.request.query_params.get('search', '')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(name_nepali__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset.order_by('name')


class StudentProfileCreateView(generics.CreateAPIView):
    """Register for साथी network"""
    serializer_class = StudentProfileCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        profile = serializer.save()
        
        # Auto-create study groups and add student
        if profile.college:
            create_auto_groups(profile)
            update_college_stats(profile.college)
        
        return profile


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_student_profile(request):
    """Get user's student profile"""
    try:
        profile = request.user.student_profile
        serializer = StudentProfileSerializer(profile)
        return Response(serializer.data)
    except StudentProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_groups(request):
    """Get user's study groups"""
    groups = request.user.study_groups.all()
    serializer = StudyGroupSerializer(groups, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def college_leaderboard(request):
    """Get college leaderboard"""
    colleges = College.objects.annotate(
        verified_students=Count('students', filter=Q(students__verification_status='APPROVED'))
    ).order_by('-verified_students')[:20]
    
    # Update ranks
    for idx, college in enumerate(colleges, 1):
        college.rank = idx
        college.total_students = college.verified_students
        college.save()
    
    serializer = CollegeLeaderboardSerializer(colleges, many=True)
    return Response(serializer.data)


# ============================================
# GROUP CHAT VIEWS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_messages(request, group_id):
    """Get group messages (HTTP Polling)"""
    group = get_object_or_404(StudyGroup, id=group_id)
    
    # Check membership
    if not group.members.filter(id=request.user.id).exists():
        return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get messages after last ID (for polling)
    after_id = request.query_params.get('after', 0)
    limit = int(request.query_params.get('limit', 50))
    
    messages = group.messages.filter(
        is_deleted=False,
        id__gt=after_id
    ).order_by('created_at')[:limit]
    
    serializer = GroupMessageSerializer(messages, many=True)
    return Response({
        'messages': serializer.data,
        'has_more': messages.count() == limit
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, group_id):
    """Send message to group"""
    group = get_object_or_404(StudyGroup, id=group_id)
    
    # Check membership
    if not group.members.filter(id=request.user.id).exists():
        return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
    
    # Check message quota
    quota, created = MessageQuota.objects.get_or_create(user=request.user)
    if not quota.check_can_send():
        return Response({
            'error': 'Daily message limit reached',
            'tier': request.user.subscription.tier if hasattr(request.user, 'subscription') else 'FREE',
            'upgrade_required': True
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Validate message
    serializer = SendMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create message
    message = GroupMessage.objects.create(
        group=group,
        sender=request.user,
        message=serializer.validated_data['message'],
        pdf_file=serializer.validated_data.get('pdf_file')
    )
    
    # Increment quota
    quota.increment()
    
    # Update group stats
    group.total_messages += 1
    group.save()
    
    return Response(GroupMessageSerializer(message).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members(request, group_id):
    """Get group members"""
    group = get_object_or_404(StudyGroup, id=group_id)
    
    members = group.members.all()
    serializer = UserSerializer(members, many=True)
    return Response(serializer.data)


# ============================================
# REFERRAL VIEWS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_referral_code(request):
    """Apply referral code (for existing users)"""
    code = request.data.get('code', '').strip()
    
    if not code:
        return Response({'error': 'Referral code required'}, status=status.HTTP_400_BAD_REQUEST)
    
    referrer = User.objects.filter(referral_code=code).first()
    if not referrer:
        return Response({'error': 'Invalid referral code'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if already referred
    if request.user.referred_by:
        return Response({'error': 'You already used a referral code'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Apply referral
    request.user.referred_by = referrer
    request.user.save()
    
    Referral.objects.create(
        referrer=referrer,
        referred=request.user,
        code_used=code
    )
    
    return Response({'message': f'Referral code applied! You were invited by {referrer.name or referrer.phone}'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_stats(request):
    """Get user's referral statistics"""
    user = request.user
    
    total = user.my_referrals.count()
    completed = user.my_referrals.filter(status='COMPLETED').count()
    pending = user.my_referrals.filter(status='PENDING').count()
    
    # Calculate rewards
    rewards_earned = user.rewards.filter(is_active=True).count()
    
    # Next reward milestone
    milestones = [1, 3, 5, 10]
    next_milestone = next((m for m in milestones if completed < m), None)
    
    return Response({
        'total_referrals': total,
        'completed_referrals': completed,
        'pending_referrals': pending,
        'total_rewards': rewards_earned,
        'next_reward_at': next_milestone,
        'referral_code': user.referral_code
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def referral_leaderboard(request):
    """Get top referrers"""
    top_users = User.objects.annotate(
        referral_count=Count('my_referrals', filter=Q(my_referrals__status='COMPLETED'))
    ).filter(referral_count__gt=0).order_by('-referral_count')[:10]
    
    leaderboard = []
    for idx, user in enumerate(top_users, 1):
        leaderboard.append({
            'rank': idx,
            'name': user.name or 'Anonymous',
            'referral_count': user.referral_count
        })
    
    return Response(leaderboard)


# ============================================
# STREAK VIEWS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_streak(request):
    """Get user's streak data"""
    streak, created = UserStreak.objects.get_or_create(user=request.user)
    serializer = UserStreakSerializer(streak)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_activity(request):
    """Log user activity (for streak)"""
    streak, created = UserStreak.objects.get_or_create(user=request.user)
    streak.log_activity()
    
    serializer = UserStreakSerializer(streak)
    return Response(serializer.data)


# ============================================
# CLOUD SYNC VIEWS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_bookmarks(request):
    """Upload/sync bookmarks"""
    bookmarks_data = request.data.get('bookmarks', [])
    
    synced_count = 0
    for item in bookmarks_data:
        pdf_id = item.get('pdf_id')
        try:
            pdf = PDFFile.objects.get(id=pdf_id)
            UserBookmark.objects.get_or_create(
                user=request.user,
                pdf=pdf
            )
            synced_count += 1
        except PDFFile.DoesNotExist:
            continue
    
    return Response({
        'message': f'Synced {synced_count} bookmarks',
        'total': synced_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bookmarks(request):
    """Get user's cloud bookmarks"""
    bookmarks = UserBookmark.objects.filter(user=request.user)
    serializer = UserBookmarkSerializer(bookmarks, many=True)
    return Response(serializer.data)


# ============================================
# USAGE / APP TIME TRACKING
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def usage_log(request):
    """
    Report app usage time (and optionally PDFs viewed) from the Flutter app.
    Call when app goes to background, or periodically (e.g. every 5 min), or when user leaves a screen.
    Time is accumulated per user per day (UTC date).
    """
    serializer = UsageLogSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    minutes = data.get('time_spent_minutes', 0)
    seconds = data.get('time_spent_seconds', 0)
    minutes += (seconds + 59) // 60  # convert seconds to minutes (round up)
    pdfs_viewed = data.get('pdfs_viewed', 0)
    topic_usage_list = data.get('topic_usage') or []

    today = timezone.now().date()
    # Update last_seen so user is counted as "online" when they send usage
    User.objects.filter(pk=request.user.pk).update(last_seen=timezone.now())

    activity, created = UserActivity.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={'pdfs_viewed': 0, 'messages_sent': 0, 'time_spent_minutes': 0}
    )
    activity.time_spent_minutes += minutes
    activity.pdfs_viewed += pdfs_viewed
    activity.save(update_fields=['time_spent_minutes', 'pdfs_viewed'])

    # Keep User.pdf_views_count in sync for admin "total PDF views per user"
    if pdfs_viewed > 0:
        User.objects.filter(pk=request.user.pk).update(pdf_views_count=F('pdf_views_count') + pdfs_viewed)

    # Save per-topic usage (which topic user used – for admin analytics)
    for item in topic_usage_list:
        topic_id = item.get('topic_id')
        usage_count = item.get('usage_count', 1)
        time_spent = item.get('time_spent_minutes', 0)
        try:
            topic = Topic.objects.get(pk=topic_id, is_approved=True)
        except Topic.DoesNotExist:
            continue
        utu, created_utu = UserTopicUsage.objects.get_or_create(
            user=request.user,
            topic=topic,
            date=today,
            defaults={'usage_count': 0, 'time_spent_minutes': 0}
        )
        utu.usage_count += usage_count
        utu.time_spent_minutes += time_spent
        utu.save(update_fields=['usage_count', 'time_spent_minutes'])

    return Response({
        'message': 'Usage logged',
        'today_minutes': activity.time_spent_minutes,
        'today_pdfs_viewed': activity.pdfs_viewed,
    }, status=status.HTTP_201_CREATED)


# ============================================
# PRESENCE (active online users)
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def presence_heartbeat(request):
    """
    Call when the app is in foreground so the user is counted as "online".
    Flutter should call this every 1–2 minutes while the app is open.
    Updates request.user.last_seen.
    """
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([AllowAny])
def presence_active_count(request):
    """
    Get count of users currently considered "online" (last_seen in the last N minutes).
    Query params: minutes (default 5).
    """
    minutes = min(60, max(1, int(request.query_params.get('minutes', 5))))
    since = timezone.now() - timedelta(minutes=minutes)
    count = User.objects.filter(last_seen__gte=since, is_active=True).count()
    return Response({'active_count': count})


# ============================================
# PDF TIME LEADERBOARD
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def leaderboard_pdf_time(request):
    """
    Leaderboard of users by total time spent in app (PDF reading).
    Query params: limit (default 50, max 100), period=all|week|month.
    Returns: [{ rank, display_name, total_minutes, total_pdfs_viewed, is_verified }].
    """
    limit = min(100, max(1, int(request.query_params.get('limit', 50))))
    period = (request.query_params.get('period') or 'all').strip().lower()
    if period not in ('all', 'week', 'month'):
        period = 'all'

    today = timezone.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    else:
        start_date = None

    if start_date:
        qs = User.objects.filter(is_active=True).annotate(
            total_minutes=Sum('activities__time_spent_minutes', filter=Q(activities__date__gte=start_date)),
            total_pdfs=Sum('activities__pdfs_viewed', filter=Q(activities__date__gte=start_date)),
        )
    else:
        qs = User.objects.filter(is_active=True).annotate(
            total_minutes=Sum('activities__time_spent_minutes'),
            total_pdfs=Sum('activities__pdfs_viewed'),
        )

    qs = qs.filter(total_minutes__gte=1).order_by('-total_minutes')[:limit]

    result = []
    for idx, user in enumerate(qs, 1):
        result.append({
            'rank': idx,
            'display_name': (user.name or '').strip() or 'Anonymous',
            'total_minutes': user.total_minutes or 0,
            'total_pdfs_viewed': user.total_pdfs or 0,
            'is_verified': getattr(user, 'is_verified', False),
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_summary(request):
    """
    Get current user's app usage summary: last N days and total time.
    Query params: days (default 30) - number of days to return.
    """
    days = min(365, max(1, int(request.query_params.get('days', 30))))
    activities = UserActivity.objects.filter(user=request.user).order_by('-date')[:days]
    serializer = UserActivitySerializer(activities, many=True)

    total_minutes = UserActivity.objects.filter(user=request.user).aggregate(
        total=Sum('time_spent_minutes')
    )['total'] or 0
    total_pdfs_viewed = UserActivity.objects.filter(user=request.user).aggregate(
        total=Sum('pdfs_viewed')
    )['total'] or 0

    return Response({
        'by_date': serializer.data,
        'total_time_minutes': total_minutes,
        'total_pdfs_viewed': total_pdfs_viewed,
    })


# ============================================
# EXISTING VIEWS (KEEP AS IS)
# ============================================

class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Topic.objects.filter(is_approved=True).order_by('name')


class SubjectByTopicView(generics.ListAPIView):
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        topic_id = self.kwargs['topic_id']
        return Subject.objects.filter(topic_id=topic_id, is_approved=True).annotate(
            has_premium_pdfs=Exists(
                PDFFile.objects.filter(subject=OuterRef('pk')).filter(Q(is_premium=True) | Q(is_solution=True))
            )
        )


class YearListBySubjectView(generics.ListAPIView):
    serializer_class = serializers.Serializer  # Custom year serializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        subject_id = self.kwargs['subject_id']
        years = PDFFile.objects.filter(subject_id=subject_id, is_approved=True)\
                              .values('year')\
                              .annotate(pdf_count=Count('id'))\
                              .order_by('-year')
        return Response(list(years))


class PDFsBySubjectAndYearView(generics.ListAPIView):
    """
    GET /api/subjects/<id>/years/<year>/pdfs/
    Query: solutions_only=true → Solution + Both PDFs. Omitted/false → Question + Both PDFs.
    Auth required. Refetch after purchase so purchased PDFs show has_access: true.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        year = self.kwargs['year']
        qs = PDFFile.objects.filter(subject_id=subject_id, year=year, is_approved=True).select_related('subject')
        solutions_only = self.request.query_params.get('solutions_only', 'false').strip().lower()
        if solutions_only == 'true':
            # Solutions tab: pure solutions + combined Q+S documents
            qs = qs.filter(pdf_type__in=['SOLUTION', 'BOTH'])
        else:
            # Questions tab: pure questions + combined Q+S documents
            qs = qs.filter(pdf_type__in=['QUESTION', 'BOTH'])
        return qs
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Pre-compute package-level access so the serializer doesn't
        # issue per-PDF queries (avoids N+1).
        package_pdf_ids = set()
        if request.user.is_authenticated:
            package_pdf_ids = get_package_accessible_pdf_ids(
                request.user, queryset
            )

        serializer = PDFFileSerializer(
            queryset,
            many=True,
            context={
                'request': request,
                'package_pdf_ids': package_pdf_ids,
            }
        )
        return Response(serializer.data)


class StatsAPIView(generics.GenericAPIView):
    """
    GET /api/stats/
    Public stats: total topics, subjects, PDFs. If authenticated: my upload counts (PDFs, topics, subjects).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        total_topics = Topic.objects.filter(is_approved=True).count()
        total_subjects = Subject.objects.filter(is_approved=True).count()
        total_pdfs = PDFFile.objects.filter(is_approved=True).count()
        student_pdf_uploads_pending = PDFFile.objects.filter(uploaded_by__isnull=False, is_approved=False).count()
        data = {
            'total_topics': total_topics,
            'total_subjects': total_subjects,
            'total_pdfs': total_pdfs,
            'student_pdf_uploads_pending': student_pdf_uploads_pending,
        }
        if request.user.is_authenticated:
            user = request.user
            data['my_pdf_uploads_count'] = PDFFile.objects.filter(uploaded_by=user).count()
            data['my_pdf_uploads_pending_count'] = PDFFile.objects.filter(uploaded_by=user, is_approved=False).count()
            data['my_topics_count'] = Topic.objects.filter(uploaded_by=user).count()
            data['my_subjects_count'] = Subject.objects.filter(uploaded_by=user).count()
        return Response(data)


class TopicCreateView(generics.CreateAPIView):
    """
    POST /api/student-topics/create/
    Student suggests a new topic. Admin must approve before it appears in app. Auth required.
    Body: { "name": "Topic Name" }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TopicCreateSerializer


class SubjectCreateView(generics.CreateAPIView):
    """
    POST /api/student-subjects/create/
    Student suggests a new subject under an approved topic. Admin must approve. Auth required.
    Body: { "name": "Subject Name", "topic": <topic_id> }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectCreateSerializer


class StudentPDFUploadView(generics.CreateAPIView):
    """
    POST /api/student-pdfs/upload/
    Student uploads a free (question) PDF. Admin must approve before it appears in the app.
    Auth required. Multipart form-data: title, subtitle (optional), year, subject, file.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = StudentPDFUploadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        out_serializer = MyPDFUploadSerializer(obj)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class MyPDFUploadsView(generics.ListAPIView):
    """
    GET /api/student-pdfs/my-uploads/
    List current user's PDF uploads (pending and approved). Auth required.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MyPDFUploadSerializer

    def get_queryset(self):
        return PDFFile.objects.filter(uploaded_by=self.request.user).select_related('subject').order_by('-created_at')


class StudentPDFDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/student-pdfs/<id>/ – Get one of current user's PDF uploads.
    PATCH /api/student-pdfs/<id>/ – Update details (title, subtitle, year, subject, optional file). Owner only.
    DELETE /api/student-pdfs/<id>/ – Delete the upload. Owner only.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MyPDFUploadSerializer

    def get_queryset(self):
        return PDFFile.objects.filter(uploaded_by=self.request.user).select_related('subject')

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return StudentPDFUpdateSerializer
        return MyPDFUploadSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = StudentPDFUpdateSerializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MyPDFUploadSerializer(instance).data)
    
    def perform_destroy(self, instance):
        instance.delete()


class FeedbackCreateView(generics.CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        try:
            serializer.save(user=user)
        except IntegrityError as e:
            raise ValidationError(
                'Database constraint failed. A related record (e.g. User) may not exist. '
                'Please ensure all references are valid. Details: %s' % str(e)
            ) from e


class FeedbackListView(generics.ListAPIView):
    queryset = Feedback.objects.all().order_by('-created_at')
    serializer_class = FeedbackSerializer
    permission_classes = [AllowAny]


class UserQueryCreateView(generics.CreateAPIView):
    queryset = UserQuery.objects.all()
    serializer_class = UserQuerySerializer
    permission_classes = [AllowAny]


# ============================================
# NOTIFICATION VIEWS (all user notifications; pin / save for later)
# ============================================

class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    List current user's notifications. Query params: ?pinned_only=1, ?unread_only=1
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).select_related('subject')
        if self.request.query_params.get('pinned_only') == '1':
            qs = qs.filter(is_pinned=True)
        if self.request.query_params.get('unread_only') == '1':
            qs = qs.filter(is_read=False)
        return qs.order_by('-created_at')


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def notification_update(request, pk):
    """
    PATCH /api/notifications/<id>/
    Mark as read and/or pin (save for later). Body: { "is_read": true, "is_pinned": true }
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    serializer = NotificationUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    if 'is_read' in serializer.validated_data:
        notification.is_read = serializer.validated_data['is_read']
    if 'is_pinned' in serializer.validated_data:
        notification.is_pinned = serializer.validated_data['is_pinned']
    notification.save()
    return Response(NotificationSerializer(notification).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    """POST /api/notifications/<id>/mark-read/ - mark single notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return Response(NotificationSerializer(notification).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_pin(request, pk):
    """POST /api/notifications/<id>/pin/ - pin (save for later)."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_pinned = True
    notification.save()
    return Response(NotificationSerializer(notification).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_unpin(request, pk):
    """POST /api/notifications/<id>/unpin/ - unpin."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_pinned = False
    notification.save()
    return Response(NotificationSerializer(notification).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    """GET /api/notifications/unread-count/ - count of unread notifications (for badge)."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'unread_count': count})


# ============================================
# SUBJECT ROUTINE VIEWS (routine per subject; start/pin reminder)
# ============================================

class SubjectRoutineListView(generics.ListAPIView):
    """
    GET /api/subjects/<subject_id>/routines/
    List routines for a subject (for student). Optional ?day=0..6 to filter by day.
    """
    serializer_class = SubjectRoutineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, pk=subject_id)
        qs = SubjectRoutine.objects.filter(subject=subject).select_related('subject')
        day = self.request.query_params.get('day')
        if day is not None:
            try:
                day = int(day)
                if 0 <= day <= 6:
                    qs = qs.filter(day_of_week=day)
            except ValueError:
                pass
        return qs.order_by('day_of_week', 'order', 'start_time')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def routine_start_reminder(request, routine_id):
    """
    POST /api/routines/<routine_id>/start-reminder/
    User subscribes to get notified before this routine (e.g. "Notify me 15 min before").
    Body: { "notify_minutes_before": 15 } (optional, default 15).
    """
    routine = get_object_or_404(SubjectRoutine, pk=routine_id)
    notify_minutes = request.data.get('notify_minutes_before', 15)
    if not isinstance(notify_minutes, int) or notify_minutes < 1 or notify_minutes > 1440:
        notify_minutes = 15
    reminder, created = UserRoutineReminder.objects.get_or_create(
        user=request.user,
        routine=routine,
        defaults={'notify_minutes_before': notify_minutes},
    )
    if not created:
        reminder.notify_minutes_before = notify_minutes
        reminder.save()
    return Response(
        UserRoutineReminderSerializer(reminder, context={'request': request}).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def routine_stop_reminder(request, routine_id):
    """POST /api/routines/<routine_id>/stop-reminder/ - stop reminder for this routine."""
    routine = get_object_or_404(SubjectRoutine, pk=routine_id)
    deleted, _ = UserRoutineReminder.objects.filter(user=request.user, routine=routine).delete()
    return Response({
        'message': 'Reminder stopped' if deleted else 'No reminder was set',
        'routine_id': routine_id,
    })


class MyRoutineRemindersView(generics.ListAPIView):
    """
    GET /api/routines/my-reminders/
    List routines the user has pinned (started reminder) for later notification.
    """
    serializer_class = UserRoutineReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserRoutineReminder.objects.filter(user=self.request.user).select_related('routine', 'routine__subject').order_by('-created_at')


# ============================================
# TU NOTICE FEED (user posts, admin approval, like, bookmark, comment)
# ============================================

def _feed_post_queryset(request, approved_only=True):
    """Base queryset for feed: approved + active. Annotate like_count, is_liked, comment_count, is_bookmarked."""
    qs = FeedPost.objects.filter(is_active=True)
    if approved_only:
        qs = qs.filter(status='APPROVED')
    qs = qs.annotate(
        _like_count=Count('likes'),
        _comment_count=Count('comments'),
    )
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        qs = qs.annotate(
            _is_liked=Exists(FeedPostLike.objects.filter(post=OuterRef('pk'), user=user)),
            _is_bookmarked=Exists(FeedPostBookmark.objects.filter(post=OuterRef('pk'), user=user)),
        )
    return qs.order_by('-created_at')


class FeedPostListView(generics.ListAPIView):
    """
    GET /api/feed/
    List approved TU Notice Feed posts. Optional auth: is_liked, is_bookmarked set when logged in.
    """
    serializer_class = FeedPostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return _feed_post_queryset(self.request, approved_only=True)


class FeedPostDetailView(generics.RetrieveAPIView):
    """
    GET /api/feed/<id>/
    Single approved feed post with like_count, is_liked, comment_count, is_bookmarked.
    """
    serializer_class = FeedPostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return _feed_post_queryset(self.request, approved_only=True)


class FeedPostCreateView(generics.CreateAPIView):
    """
    POST /api/feed/create/
    Create a TU Notice post (multipart: images [up to 10], title, description). Status = PENDING until admin approves.
    """
    serializer_class = FeedPostCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post = serializer.save(created_by=self.request.user, status='PENDING')
        # Accept up to 10 images via multipart field 'images' (multiple files)
        for order, file in enumerate(self.request.FILES.getlist('images')[:10]):
            FeedPostImage.objects.create(post=post, image=file, order=order)


class MyFeedPostsListView(generics.ListAPIView):
    """
    GET /api/feed/my-posts/
    List current user's TU Notice posts (all statuses: PENDING, APPROVED, REJECTED).
    """
    serializer_class = FeedPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _feed_post_queryset(self.request, approved_only=False).filter(created_by=self.request.user)


class MyFeedBookmarksListView(generics.ListAPIView):
    """
    GET /api/feed/bookmarks/
    List feed posts that the current user has bookmarked (approved posts only, newest first).
    """
    serializer_class = FeedPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _feed_post_queryset(self.request, approved_only=True).filter(
            bookmarks__user=self.request.user
        ).distinct()


@api_view(['DELETE', 'POST'])
@permission_classes([IsAuthenticated])
def feed_post_delete(request, pk):
    """
    DELETE /api/feed/<id>/delete/ – Delete a TU Notice post. Only the user who created it can delete.
    """
    post = get_object_or_404(FeedPost, pk=pk)
    if post.created_by_id != request.user.id:
        raise PermissionDenied('You can only delete your own posts.')
    post.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def feed_post_approve(request, pk):
    """
    POST /api/feed/<id>/approve/
    Admin only. Set post status to APPROVED so it appears in the feed.
    """
    post = get_object_or_404(FeedPost, pk=pk)
    post.status = 'APPROVED'
    post.is_active = True
    post.save(update_fields=['status', 'is_active', 'updated_at'])
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def feed_post_reject(request, pk):
    """
    POST /api/feed/<id>/reject/
    Admin only. Set post status to REJECTED (hidden from feed).
    """
    post = get_object_or_404(FeedPost, pk=pk)
    post.status = 'REJECTED'
    post.save(update_fields=['status', 'updated_at'])
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feed_post_like(request, pk):
    """
    POST /api/feed/<id>/like/
    Like the post (idempotent: already liked is 200). Only approved posts.
    """
    post = get_object_or_404(FeedPost, pk=pk, is_active=True, status='APPROVED')
    _, created = FeedPostLike.objects.get_or_create(user=request.user, post=post)
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feed_post_unlike(request, pk):
    """
    POST /api/feed/<id>/unlike/
    Remove like. Returns updated post.
    """
    post = get_object_or_404(FeedPost, pk=pk, is_active=True, status='APPROVED')
    FeedPostLike.objects.filter(user=request.user, post=post).delete()
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feed_post_bookmark(request, pk):
    """
    POST /api/feed/<id>/bookmark/
    Bookmark the post (idempotent). Only approved posts.
    """
    post = get_object_or_404(FeedPost, pk=pk, is_active=True, status='APPROVED')
    _, created = FeedPostBookmark.objects.get_or_create(user=request.user, post=post)
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feed_post_unbookmark(request, pk):
    """
    POST /api/feed/<id>/unbookmark/
    Remove bookmark.
    """
    post = get_object_or_404(FeedPost, pk=pk, is_active=True, status='APPROVED')
    FeedPostBookmark.objects.filter(user=request.user, post=post).delete()
    return Response(
        FeedPostSerializer(post, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


class FeedPostCommentListCreateView(generics.ListCreateAPIView):
    """
    GET /api/feed/<id>/comments/ – List comments for an approved feed post.
    POST /api/feed/<id>/comments/ – Add a comment (auth required). Body: { "text": "..." }
    """
    serializer_class = FeedPostCommentSerializer
    permission_classes = [AllowAny]  # GET allowed for all; POST requires auth (serializer/validation can check)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        return FeedPostComment.objects.filter(
            post_id=self.kwargs['pk'],
            post__status='APPROVED',
            post__is_active=True,
        ).select_related('user').order_by('created_at')

    def perform_create(self, serializer):
        post = get_object_or_404(FeedPost, pk=self.kwargs['pk'], is_active=True, status='APPROVED')
        serializer.save(user=self.request.user, post=post)