# ========================================
# DJANGO BACKEND - urls.py
# ========================================
# Location: pdf_app/urls.py
# Complete URL routing for all APIs
# ========================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from pdf_app import views

# Router for ViewSets
router = DefaultRouter()
router.register(r'topics', views.TopicViewSet, basename='topic')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # ========================================
    # AUTHENTICATION APIs (Password-based; OTP only for forgot password)
    # ========================================
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/forgot-password/send-otp/', views.forgot_password_send_otp, name='forgot-password-send-otp'),
    path('auth/forgot-password/reset/', views.forgot_password_reset, name='forgot-password-reset'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='token-logout'),
    path('auth/me/', views.current_user, name='current-user'),
    path('auth/update/', views.update_user, name='update-user'),
    
    # ========================================
    # PAYMENT APIs (QR Payment System)
    # ========================================
    path('payment/qr/', views.payment_qr, name='payment-qr'),
    path('payment/create/', views.PaymentCreateView.as_view(), name='payment-create'),
    path('payment/my-payments/', views.MyPaymentsView.as_view(), name='my-payments'),
    path('payment/status/<uuid:payment_id>/', views.payment_status, name='payment-status'),
    path('payment/verify/', views.verify_payment, name='payment-verify'),
    
    # ========================================
    # SUBSCRIPTION APIs
    # ========================================
    path('subscription/plans/', views.subscription_plans, name='subscription-plans'),
    path('subscription/packages/', views.subscription_packages, name='subscription-packages'),
    path('subscription/my-subscription/', views.my_subscription, name='my-subscription'),
    path('subscription/check-access/<int:pdf_id>/', views.check_pdf_access, name='check-pdf-access'),
    path('subscription/messages-remaining/', views.messages_remaining, name='messages-remaining'),
    
    # ========================================
    # COLLEGE & साथी APIs
    # ========================================
    path('colleges/', views.CollegeListView.as_view(), name='college-list'),
    path('student-profile/create/', views.StudentProfileCreateView.as_view(), name='student-profile-create'),
    path('student-profile/me/', views.my_student_profile, name='my-student-profile'),
    path('my-groups/', views.my_groups, name='my-groups'),
    path('leaderboard/', views.college_leaderboard, name='college-leaderboard'),
    
    # ========================================
    # CHAT APIs (HTTP Polling)
    # ========================================
    path('chat/<int:group_id>/messages/', views.group_messages, name='group-messages'),
    path('chat/<int:group_id>/send/', views.send_message, name='send-message'),
    path('chat/<int:group_id>/members/', views.group_members, name='group-members'),
    
    # ========================================
    # REFERRAL APIs
    # ========================================
    path('referral/apply-code/', views.apply_referral_code, name='apply-referral-code'),
    path('referral/my-stats/', views.referral_stats, name='referral-stats'),
    path('referral/leaderboard/', views.referral_leaderboard, name='referral-leaderboard'),
    
    # ========================================
    # STREAK APIs
    # ========================================
    path('streak/my-streak/', views.my_streak, name='my-streak'),
    path('streak/log-activity/', views.log_activity, name='log-activity'),
    
    # ========================================
    # CLOUD SYNC APIs
    # ========================================
    path('sync/bookmarks/', views.sync_bookmarks, name='sync-bookmarks'),
    path('bookmarks/', views.get_bookmarks, name='get-bookmarks'),

    # ========================================
    # USAGE / APP TIME TRACKING
    # ========================================
    path('usage/log/', views.usage_log, name='usage-log'),
    path('usage/summary/', views.usage_summary, name='usage-summary'),
    
    # ========================================
    # STATS API (dashboard / home)
    # ========================================
    path('stats/', views.StatsAPIView.as_view(), name='stats'),

    # ========================================
    # STUDENT-CREATED TOPICS & SUBJECTS (admin approval)
    # ========================================
    path('student-topics/create/', views.TopicCreateView.as_view(), name='student-topic-create'),
    path('student-subjects/create/', views.SubjectCreateView.as_view(), name='student-subject-create'),

    # ========================================
    # STUDENT PDF UPLOAD (free PDFs, admin approval)
    # ========================================
    path('student-pdfs/upload/', views.StudentPDFUploadView.as_view(), name='student-pdf-upload'),
    path('student-pdfs/my-uploads/', views.MyPDFUploadsView.as_view(), name='my-pdf-uploads'),

    # ========================================
    # EXISTING PDF APIs
    # ========================================
    path('topics/<int:topic_id>/subjects/', views.SubjectByTopicView.as_view(), name='subjects-by-topic'),
    path('subjects/<int:subject_id>/years/', views.YearListBySubjectView.as_view(), name='years-by-subject'),
    path('subjects/<int:subject_id>/years/<int:year>/pdfs/', views.PDFsBySubjectAndYearView.as_view(), name='pdfs-by-subject-year'),
    
    # ========================================
    # FEEDBACK APIs
    # ========================================
    path('feedback/', views.FeedbackCreateView.as_view(), name='feedback-create'),
    path('feedback/list/', views.FeedbackListView.as_view(), name='feedback-list'),
    path('user-query/', views.UserQueryCreateView.as_view(), name='user-query-create'),
]

# ========================================
# URL PATTERNS SUMMARY
# ========================================
# Total APIs: 30+
#
# Authentication: 7 endpoints (register, login, forgot-password x2, refresh, me, update)
# Payment: 4 endpoints
# Subscription: 4 endpoints
# साथी/College: 5 endpoints
# Chat: 3 endpoints
# Referral: 3 endpoints
# Streak: 2 endpoints
# Sync: 2 endpoints
# PDF: 4 endpoints
# Feedback: 3 endpoints
# ========================================