# pdf_app/utils.py - HELPER FUNCTIONS

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import *

# ============================================
# OTP DELIVERY (forgot password)
# ============================================
# Twilio removed for production. Plug in your 3rd party SMS/OTP API here when ready.


def send_whatsapp_otp(phone, otp):
    """
    Send OTP to the user (forgot password).
    Currently prints OTP to terminal only. Replace with your SMS/OTP provider later.
    """
    if getattr(settings, 'DEBUG_PRINT_OTP', True):
        print(f"📱 OTP for {phone}: {otp}")
    # TODO: Integrate 3rd party SMS/OTP API here (e.g. send to phone via SMS gateway)
    return True


# ============================================
# साथी AUTO GROUP CREATION
# ============================================

def create_auto_groups(student_profile):
    """
    Auto-create and add student to 3 groups:
    1. Main college group
    2. Program group (BBS, BCA, etc.)
    3. Year group (3rd Year BBS)
    """
    college = student_profile.college
    program = student_profile.program
    year = student_profile.year
    user = student_profile.user
    
    # 1. College Group
    college_group, created = StudyGroup.objects.get_or_create(
        college=college,
        group_type='COLLEGE',
        defaults={'name': f"{college.name} - All Students"}
    )
    college_group.members.add(user)
    
    # 2. Program Group
    if program:
        program_group, created = StudyGroup.objects.get_or_create(
            college=college,
            group_type='PROGRAM',
            program=program,
            defaults={'name': f"{college.name} - {program}"}
        )
        program_group.members.add(user)
    
    # 3. Year Group
    if program and year:
        year_group, created = StudyGroup.objects.get_or_create(
            college=college,
            group_type='YEAR',
            program=program,
            year=year,
            defaults={'name': f"{college.name} - {program} Year {year}"}
        )
        year_group.members.add(user)


# ============================================
# COLLEGE STATISTICS
# ============================================

def update_college_stats(college):
    """Update college statistics"""
    total_students = college.students.filter(
        verification_status='APPROVED'
    ).count()
    
    college.total_students = total_students
    college.save()


# ============================================
# PACKAGE ACCESS – PDFs to unlock when package payment approved
# ============================================

def get_pdfs_for_package(package):
    """
    Return queryset of PDFs included in this package.
    Uses package.pdfs (M2M). If empty, fallback by package_type:
    SUBJECT -> subject_id, TOPIC -> topic_id, YEAR -> year, ALL_YEARS -> all PDFs.
    Respects content_type (ALL / SOLUTIONS / QUESTIONS).
    """
    if package.pdfs.exists():
        qs = package.pdfs.all()
    elif package.package_type == 'SUBJECT' and package.subject_id:
        qs = PDFFile.objects.filter(subject_id=package.subject_id)
    elif package.package_type == 'TOPIC' and package.topic_id:
        qs = PDFFile.objects.filter(subject__topic_id=package.topic_id)
    elif package.package_type == 'YEAR' and package.year:
        qs = PDFFile.objects.filter(year=package.year)
    elif package.package_type == 'ALL_YEARS':
        qs = PDFFile.objects.all()
    else:
        return PDFFile.objects.none()

    # Filter by content_type (BOTH PDFs are included in both QUESTIONS and SOLUTIONS)
    if package.content_type == 'SOLUTIONS':
        qs = qs.filter(pdf_type__in=['SOLUTION', 'BOTH'])
    elif package.content_type == 'QUESTIONS':
        qs = qs.filter(pdf_type__in=['QUESTION', 'BOTH'])

    return qs


# ============================================
# RUNTIME PACKAGE ACCESS CHECKS
# ============================================

def get_user_active_packages(user):
    """
    Return list of dicts describing the user's approved package purchases.
    One DB query; results can be reused for many PDF checks.
    """
    payments = Payment.objects.filter(
        user=user,
        status='APPROVED',
        payment_type__in=[
            'SUBJECT_PACKAGE', 'TOPIC_PACKAGE',
            'YEAR_PACKAGE', 'FULL_PACKAGE',
        ],
        purchased_package__isnull=False,
    ).select_related('purchased_package')

    packages = []
    for p in payments:
        pkg = p.purchased_package
        packages.append({
            'package_type': pkg.package_type,
            'subject_id': pkg.subject_id,
            'topic_id': pkg.topic_id,
            'year': pkg.year,
            'content_type': pkg.content_type,
        })
    return packages


def pdf_covered_by_package(pdf, package_info):
    """
    Check if a single PDF is covered by a package (represented as a dict
    from get_user_active_packages).
    """
    # Content-type gate (BOTH PDFs are covered by both QUESTIONS and SOLUTIONS packages)
    ct = package_info['content_type']
    pdf_type = getattr(pdf, 'pdf_type', 'SOLUTION' if pdf.is_solution else 'QUESTION')
    if ct == 'SOLUTIONS' and pdf_type not in ('SOLUTION', 'BOTH'):
        return False
    if ct == 'QUESTIONS' and pdf_type not in ('QUESTION', 'BOTH'):
        return False

    pt = package_info['package_type']
    if pt == 'ALL_YEARS':
        return True
    if pt == 'SUBJECT' and package_info['subject_id'] == pdf.subject_id:
        return True
    if pt == 'YEAR' and package_info['year'] == pdf.year:
        return True
    if pt == 'TOPIC' and package_info['topic_id']:
        try:
            return pdf.subject.topic_id == package_info['topic_id']
        except Exception:
            return False
    return False


def get_package_accessible_pdf_ids(user, pdf_queryset):
    """
    For a queryset of PDFs, return the set of PDF IDs the user can access
    via approved package purchases.  Two DB queries total (one for packages,
    one for evaluating the queryset).
    """
    packages = get_user_active_packages(user)
    if not packages:
        return set()

    accessible = set()
    for pdf in pdf_queryset.select_related('subject'):
        for pkg in packages:
            if pdf_covered_by_package(pdf, pkg):
                accessible.add(pdf.id)
                break
    return accessible


# ============================================
# SUBSCRIPTION ACCESS GRANT
# ============================================

def grant_subscription_access(payment):
    """
    Grant subscription access when payment approved
    Called from views.py after admin approves payment
    """
    user = payment.user
    tier = payment.tier
    
    # Get or create subscription
    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={'tier': tier}
    )
    
    # Update subscription
    subscription.tier = tier
    subscription.started_at = timezone.now()
    
    # Set expiry (6 months for paid tiers)
    if tier in ['GOLD', 'DIAMOND']:
        subscription.expires_at = timezone.now() + timedelta(days=180)
    
    subscription.is_active = True
    subscription.last_payment = payment
    subscription.save()
    
    # Reset message quota to new limit
    quota, created = MessageQuota.objects.get_or_create(user=user)
    quota.messages_sent_today = 0
    quota.save()