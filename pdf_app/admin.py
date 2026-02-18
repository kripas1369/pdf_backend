# ========================================
# DJANGO BACKEND - admin.py
# ========================================
# Location: pdf_app/admin.py
# Admin panel with payment verification
# ========================================

from decimal import Decimal
from django import forms
from django.contrib import admin
from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from pdf_app.models import *
from pdf_app.utils import grant_subscription_access, create_auto_groups, update_college_stats, get_pdfs_for_package


# ========================================
# INTEGRITY ERROR MIXIN (friendly FK constraint messages)
# ========================================

class IntegrityErrorMixin:
    """Catches IntegrityError (e.g. FOREIGN KEY constraint) and shows a clear, actionable message."""

    def get_integrity_error_message(self, exc, context='save'):
        return (
            'Database constraint failed. '
            'A related record (Subject, Topic, User, or PDF) may have been deleted. '
            'Please ensure all selected references still exist. '
            f'Details: {exc}'
        )

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except IntegrityError as e:
            msg = self.get_integrity_error_message(e, 'save')
            self.message_user(request, msg, messages.ERROR)
            raise ValueError(msg) from e

    def save_related(self, request, form, formsets, change):
        """Catch IntegrityError from inline formsets and M2M saves."""
        try:
            super().save_related(request, form, formsets, change)
        except IntegrityError as e:
            msg = self.get_integrity_error_message(e, 'save')
            self.message_user(request, msg, messages.ERROR)
            raise ValueError(msg) from e

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Wrap save in transaction.atomic so failed saves roll back completely."""
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    return super().changeform_view(request, object_id, form_url, extra_context)
            except (ValueError, IntegrityError) as e:
                # Already messaged in save_model/save_related; re-raise so admin shows error
                if isinstance(e, IntegrityError):
                    self.message_user(
                        request,
                        self.get_integrity_error_message(e, 'save'),
                        messages.ERROR
                    )
                raise
        return super().changeform_view(request, object_id, form_url, extra_context)

    def delete_model(self, request, obj):
        try:
            super().delete_model(request, obj)
        except IntegrityError as e:
            msg = (
                'Cannot delete: other records depend on this (e.g. PDFs, Subjects, Payments). '
                'Delete dependent records first, or fix relations. '
                f'Details: {e}'
            )
            self.message_user(request, msg, messages.ERROR)
            raise ValueError(msg) from e

    def delete_queryset(self, request, queryset):
        try:
            super().delete_queryset(request, queryset)
        except IntegrityError as e:
            msg = (
                'Cannot delete: some records are referenced elsewhere. '
                'Delete dependent records first. '
                f'Details: {e}'
            )
            self.message_user(request, msg, messages.ERROR)
            raise ValueError(msg) from e


# ========================================
# PAYMENT QR ADMIN (Upload QR for users to scan)
# ========================================

@admin.register(PaymentQR)
class PaymentQRAdmin(admin.ModelAdmin):
    """Upload the payment QR code - shown in app when user pays"""
    
    list_display = ['qr_preview', 'instructions', 'is_active', 'updated_at']
    
    fields = ['qr_image', 'qr_preview', 'instructions', 'is_active']
    readonly_fields = ['qr_preview']
    
    def qr_preview(self, obj):
        if obj and obj.pk and obj.qr_image:
            return format_html(
                '<img src="{}" style="max-width:200px;height:auto;border-radius:8px;"/>',
                obj.qr_image.url
            )
        return 'Upload and save to see preview'
    qr_preview.short_description = 'QR Preview'


# ========================================
# PDF PACKAGE ADMIN (Subject / Year packages – select PDFs)
# ========================================

def _get_year_choices():
    """Years that exist in PDFFile."""
    years = PDFFile.objects.values_list('year', flat=True).distinct().order_by('-year')
    year_list = [(y, str(y)) for y in years] or [(timezone.now().year, str(timezone.now().year))]
    return [('', '— Select year (for Year package only)')] + year_list


class PDFPackageAdminForm(forms.ModelForm):
    """Simple: Subject package (select subject) or Year package (select year). Content: All / Questions only / Solutions only."""
    year = forms.TypedChoiceField(
        coerce=lambda x: int(x) if x and str(x).strip() else None,
        choices=[],
        required=False,
        empty_value=None,
    )

    class Meta:
        model = PDFPackage
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year'].choices = _get_year_choices()
        self.fields['subject'].required = False

    def clean(self):
        data = super().clean()
        pkg_type = data.get('package_type')
        year = data.get('year')
        subject = data.get('subject')
        topic = data.get('topic')
        if pkg_type == 'SUBJECT':
            if not subject:
                raise forms.ValidationError({'subject': 'Select a subject for Subject package.'})
            if not Subject.objects.filter(pk=subject.pk).exists():
                raise forms.ValidationError({'subject': 'Selected subject no longer exists. Choose another.'})
            data['year'] = None
            data['topic'] = None
        elif pkg_type == 'TOPIC':
            if not topic:
                raise forms.ValidationError({'topic': 'Select a topic for Topic package.'})
            if not Topic.objects.filter(pk=topic.pk).exists():
                raise forms.ValidationError({'topic': 'Selected topic no longer exists. Choose another.'})
            data['subject'] = None
            data['year'] = None
        elif pkg_type == 'YEAR':
            if not year:
                raise forms.ValidationError({'year': 'Select a year for Year package.'})
            data['subject'] = None
            data['topic'] = None
        elif pkg_type == 'ALL_YEARS':
            data['subject'] = None
            data['topic'] = None
            data['year'] = None
        return data


@admin.register(PDFPackage)
class PDFPackageAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    """Simple packages: Subject package (all PDFs in one subject) or Year package (all PDFs in one year). Content = All / Questions / Solutions."""
    form = PDFPackageAdminForm
    list_display = ['name', 'package_type', 'content_type_display', 'topic', 'subject', 'year', 'price', 'pdf_count_display', 'is_active', 'created_at']
    list_filter = ['package_type', 'content_type', 'is_active', 'topic', 'year']
    search_fields = ['name', 'subject__name', 'topic__name']
    filter_horizontal = ['pdfs']
    list_editable = ['is_active', 'price']
    ordering = ['-year', 'name']
    
    fieldsets = (
        ('1. Package type and scope', {
            'fields': ('name', 'package_type', 'topic', 'subject', 'year', 'content_type', 'price', 'is_active'),
            'description': (
                'Subject package: Select one Subject – all PDFs in that subject (all years). '
                'Topic package: Select one Topic – all subjects under that topic, all PDFs. '
                'Year package: Select one Year – all PDFs in that year (all subjects). '
                'Content type: All PDFs, Questions only, or Solutions only.'
            ),
        }),
        ('2. PDFs in this package (auto-filled on Save)', {
            'fields': ('pdfs',),
            'description': 'Click Save to auto-fill PDFs based on Subject or Year and Content type. You can add or remove PDFs after if needed.',
        }),
    )
    
    def content_type_display(self, obj):
        return obj.get_content_type_display() if obj else '-'
    content_type_display.short_description = 'Content'
    
    def pdf_count_display(self, obj):
        return obj.pdf_count()
    pdf_count_display.short_description = 'PDFs'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from pdf_app.models import PDFFile
        content = getattr(obj, 'content_type', 'ALL')
        if obj.package_type == 'SUBJECT' and obj.subject_id:
            qs = PDFFile.objects.filter(subject_id=obj.subject_id)
            if content == 'QUESTIONS':
                qs = qs.filter(pdf_type__in=['QUESTION', 'BOTH'])
            elif content == 'SOLUTIONS':
                qs = qs.filter(pdf_type__in=['SOLUTION', 'BOTH'])
            obj.pdfs.set(list(qs.values_list('pk', flat=True)))
        elif obj.package_type == 'TOPIC' and obj.topic_id:
            qs = PDFFile.objects.filter(subject__topic_id=obj.topic_id)
            if content == 'QUESTIONS':
                qs = qs.filter(pdf_type__in=['QUESTION', 'BOTH'])
            elif content == 'SOLUTIONS':
                qs = qs.filter(pdf_type__in=['SOLUTION', 'BOTH'])
            obj.pdfs.set(list(qs.values_list('pk', flat=True)))
        elif obj.package_type == 'YEAR' and obj.year:
            qs = PDFFile.objects.filter(year=obj.year)
            if content == 'QUESTIONS':
                qs = qs.filter(pdf_type__in=['QUESTION', 'BOTH'])
            elif content == 'SOLUTIONS':
                qs = qs.filter(pdf_type__in=['SOLUTION', 'BOTH'])
            obj.pdfs.set(list(qs.values_list('pk', flat=True)))


# ========================================
# PAYMENT + PDF ACCESS ADMIN (same section)
# ========================================

class PdfAccessInline(admin.TabularInline):
    """Show PDF access granted by this payment (same page as Payment; many for package)"""
    model = PdfAccess
    fk_name = 'payment'
    extra = 0
    max_num = 100
    can_delete = True
    readonly_fields = ['user', 'pdf', 'granted_at']
    fields = ['user', 'pdf', 'granted_at']
    verbose_name = 'PDF access granted'
    verbose_name_plural = 'PDF access granted by this payment'

    def has_add_permission(self, request, obj=None):
        return False  # Created only when payment is approved


@admin.register(Payment)
class PaymentAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    """Admin panel for payment verification + PDF access in one place"""
    
    inlines = [PdfAccessInline]
    
    list_display = [
        'payment_id_short',
        'user_phone',
        'payment_type',
        'tier_display_col',
        'amount',
        'purchased_pdf',
        'purchased_package',
        'screenshot_thumb',
        'status_badge',
        'payment_method',
        'created_at',
        'action_buttons'
    ]
    
    list_filter = [
        'status',
        'tier',
        'payment_type',
        'payment_method',
        'created_at'
    ]
    
    search_fields = [
        'user__phone',
        'user__name',
        'payment_id',
        'transaction_note'
    ]
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ['payment_id', 'created_at', 'updated_at', 'screenshot_preview', 'verified_by', 'verified_at']
        if obj:  # Editing existing payment – don't allow changing user
            readonly = ['user'] + readonly
        return readonly
    
    fields = [
        'payment_id',
        'user',
        'payment_type',
        'tier',
        'amount',
        'purchased_pdf',
        'purchased_package',
        'payment_method',
        'transaction_note',
        'screenshot_preview',
        'status',
        'admin_notes',
        'verified_by',
        'verified_at',
        'created_at',
        'updated_at'
    ]
    
    actions = ['approve_payments', 'reject_payments']
    
    def payment_id_short(self, obj):
        """Show shortened payment ID"""
        return str(obj.payment_id)[:8]
    payment_id_short.short_description = 'Payment ID'
    
    def user_phone(self, obj):
        """Show user phone"""
        return obj.user.phone
    user_phone.short_description = 'Phone'
    
    def tier_display_col(self, obj):
        """Show tier"""
        return obj.get_tier_display() if obj.tier else '-'
    tier_display_col.short_description = 'Tier'
    
    def screenshot_thumb(self, obj):
        """Show screenshot thumbnail"""
        if obj.screenshot:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;"/>'
                '</a>',
                obj.screenshot.url,
                obj.screenshot.url
            )
        return '-'
    screenshot_thumb.short_description = 'Screenshot'
    
    def screenshot_preview(self, obj):
        """Show full screenshot preview"""
        if obj.screenshot:
            return format_html(
                '<img src="{}" style="max-width:500px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);"/>',
                obj.screenshot.url
            )
        return 'No screenshot'
    screenshot_preview.short_description = 'Screenshot Preview'
    
    def status_badge(self, obj):
        """Show colored status badge"""
        colors = {
            'PENDING': '#FFA500',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545'
        }
        return format_html(
            '<span style="background:{}; color:white; padding:5px 10px; border-radius:4px; font-weight:bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def action_buttons(self, obj):
        """Show approve/reject buttons for pending payments"""
        if obj.status == 'PENDING':
            return format_html(
                '<a class="button" style="background:#28a745; color:white; padding:5px 10px; '
                'border-radius:4px; margin-right:5px; text-decoration:none;" '
                'href="{}approve/">✓ Approve</a>'
                '<a class="button" style="background:#dc3545; color:white; padding:5px 10px; '
                'border-radius:4px; text-decoration:none;" '
                'href="{}reject/">✗ Reject</a>',
                obj.pk,
                obj.pk
            )
        return format_html(
            '<span style="color:#666;">-</span>'
        )
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        """Add custom URLs for approve/reject"""
        urls = super().get_urls()
        custom_urls = [
            path('<int:payment_id>/approve/', self.admin_site.admin_view(self.approve_payment), name='payment-approve'),
            path('<int:payment_id>/reject/', self.admin_site.admin_view(self.reject_payment), name='payment-reject'),
        ]
        return custom_urls + urls
    
    def approve_payment(self, request, payment_id):
        """Approve payment and grant access (subscription or unlock PDF)"""
        payment = Payment.objects.get(pk=payment_id)
        payment.status = 'APPROVED'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save()
        
        if payment.payment_type == 'SUBSCRIPTION':
            grant_subscription_access(payment)
        elif payment.payment_type == 'SINGLE_PDF' and payment.purchased_pdf:
            PdfAccess.objects.get_or_create(
                user=payment.user,
                pdf=payment.purchased_pdf,
                defaults={'payment': payment}
            )
        elif payment.payment_type in ('SUBJECT_PACKAGE', 'TOPIC_PACKAGE', 'YEAR_PACKAGE', 'FULL_PACKAGE') and payment.purchased_package:
            for pdf in get_pdfs_for_package(payment.purchased_package):
                PdfAccess.objects.get_or_create(
                    user=payment.user,
                    pdf=pdf,
                    defaults={'payment': payment}
                )
        
        messages.success(request, f'Payment {str(payment.payment_id)[:8]} approved successfully!')
        return redirect('admin:pdf_app_payment_change', payment_id)
    
    def reject_payment(self, request, payment_id):
        """Reject payment"""
        payment = Payment.objects.get(pk=payment_id)
        payment.status = 'REJECTED'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save()
        
        messages.warning(request, f'Payment {str(payment.payment_id)[:8]} rejected.')
        return redirect('admin:pdf_app_payment_change', payment_id)
    
    def approve_payments(self, request, queryset):
        """Bulk approve payments and grant access (subscription or unlock PDF)"""
        count = 0
        for payment in queryset.filter(status='PENDING'):
            payment.status = 'APPROVED'
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.save()
            
            if payment.payment_type == 'SUBSCRIPTION':
                grant_subscription_access(payment)
            elif payment.payment_type == 'SINGLE_PDF' and payment.purchased_pdf:
                PdfAccess.objects.get_or_create(
                    user=payment.user,
                    pdf=payment.purchased_pdf,
                    defaults={'payment': payment}
                )
            elif payment.payment_type in ('SUBJECT_PACKAGE', 'TOPIC_PACKAGE', 'YEAR_PACKAGE', 'FULL_PACKAGE') and payment.purchased_package:
                for pdf in get_pdfs_for_package(payment.purchased_package):
                    PdfAccess.objects.get_or_create(
                        user=payment.user,
                        pdf=pdf,
                        defaults={'payment': payment}
                    )
            
            count += 1
        
        self.message_user(request, f'{count} payment(s) approved successfully!')
    approve_payments.short_description = '✓ Approve selected payments'
    
    def reject_payments(self, request, queryset):
        """Bulk reject payments"""
        count = queryset.filter(status='PENDING').update(
            status='REJECTED',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{count} payment(s) rejected.')
    reject_payments.short_description = '✗ Reject selected payments'

    def save_model(self, request, obj, form, change):
        """When status is set to APPROVED (via form or any path), set verified_* and grant access so has_access is true for that user."""
        if obj.status == 'APPROVED' and (not obj.verified_by or not obj.verified_at):
            obj.verified_by = request.user
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.status == 'APPROVED':
            if obj.payment_type == 'SUBSCRIPTION':
                grant_subscription_access(obj)
            elif obj.payment_type == 'SINGLE_PDF' and obj.purchased_pdf_id:
                PdfAccess.objects.get_or_create(
                    user=obj.user,
                    pdf=obj.purchased_pdf,
                    defaults={'payment': obj}
                )
            elif obj.payment_type in ('SUBJECT_PACKAGE', 'TOPIC_PACKAGE', 'YEAR_PACKAGE', 'FULL_PACKAGE') and obj.purchased_package_id:
                for pdf in get_pdfs_for_package(obj.purchased_package):
                    PdfAccess.objects.get_or_create(
                        user=obj.user,
                        pdf=pdf,
                        defaults={'payment': obj}
                    )


# ========================================
# STUDENT PROFILE ADMIN
# ========================================

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin panel for student verification"""
    
    list_display = [
        'user_phone',
        'college_name',
        'program',
        'year',
        'section',
        'verification_badge',
        'photo_thumb',
        'created_at'
    ]
    
    list_filter = [
        'verification_status',
        'college',
        'program',
        'year'
    ]
    
    search_fields = [
        'user__phone',
        'user__name',
        'college__name'
    ]
    
    readonly_fields = [
        'user',
        'photo_preview',
        'verified_at',
        'created_at'
    ]
    
    actions = ['approve_profiles', 'reject_profiles']
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = 'Phone'
    
    def college_name(self, obj):
        return obj.college.name if obj.college else '-'
    college_name.short_description = 'College'
    
    def verification_badge(self, obj):
        """Show colored verification status"""
        colors = {
            'PENDING': '#FFA500',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545'
        }
        return format_html(
            '<span style="background:{}; color:white; padding:4px 8px; border-radius:4px; font-size:11px;">{}</span>',
            colors.get(obj.verification_status, '#666'),
            obj.get_verification_status_display()
        )
    verification_badge.short_description = 'Status'
    
    def photo_thumb(self, obj):
        """Show ID card thumbnail"""
        if obj.verification_photo:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;"/>',
                obj.verification_photo.url
            )
        return '-'
    photo_thumb.short_description = 'ID Card'
    
    def photo_preview(self, obj):
        """Show full ID card preview"""
        if obj.verification_photo:
            return format_html(
                '<img src="{}" style="max-width:400px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);"/>',
                obj.verification_photo.url
            )
        return 'No photo uploaded'
    photo_preview.short_description = 'ID Card Preview'
    
    def approve_profiles(self, request, queryset):
        """Bulk approve profiles"""
        count = 0
        for profile in queryset.filter(verification_status='PENDING'):
            profile.verification_status = 'APPROVED'
            profile.verified_at = timezone.now()
            profile.save()
            
            # Create auto-groups
            create_auto_groups(profile)
            
            # Update college stats
            if profile.college:
                update_college_stats(profile.college)
            
            count += 1
        
        self.message_user(request, f'{count} profile(s) approved successfully!')
    approve_profiles.short_description = '✓ Approve selected profiles'
    
    def reject_profiles(self, request, queryset):
        """Bulk reject profiles"""
        count = queryset.filter(verification_status='PENDING').update(
            verification_status='REJECTED',
            verified_at=timezone.now()
        )
        self.message_user(request, f'{count} profile(s) rejected.')
    reject_profiles.short_description = '✗ Reject selected profiles'


# ========================================
# SUBSCRIPTION ADMIN
# ========================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_phone', 'tier', 'is_active', 'started_at', 'expires_at', 'days_remaining']
    list_filter = ['tier', 'is_active']
    search_fields = ['user__phone', 'user__name']
    readonly_fields = ['started_at']
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = 'Phone'
    
    def days_remaining(self, obj):
        if not obj.expires_at:
            return '∞'
        days = (obj.expires_at - timezone.now()).days
        return max(0, days)
    days_remaining.short_description = 'Days Left'


# ========================================
# COLLEGE ADMIN
# ========================================

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'district', 'total_students', 'rank']
    list_filter = ['district']
    search_fields = ['name', 'name_nepali', 'location']
    actions = ['update_stats']
    
    def update_stats(self, request, queryset):
        """Update student count and rank"""
        for college in queryset:
            update_college_stats(college)
        self.message_user(request, f'{queryset.count()} college(s) updated!')
    update_stats.short_description = 'Update statistics'


# ========================================
# STUDY GROUP ADMIN
# ========================================

@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'college', 'group_type', 'program', 'year', 'member_count', 'total_messages']
    list_filter = ['group_type', 'college', 'program']
    search_fields = ['name', 'college__name']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


# ========================================
# GROUP MESSAGE ADMIN
# ========================================

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['sender_phone', 'group_name', 'message_preview', 'created_at', 'is_deleted']
    list_filter = ['group', 'is_deleted', 'created_at']
    search_fields = ['sender__phone', 'message']
    readonly_fields = ['created_at']
    
    def sender_phone(self, obj):
        return obj.sender.phone
    sender_phone.short_description = 'Sender'
    
    def group_name(self, obj):
        return obj.group.name
    group_name.short_description = 'Group'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


# ========================================
# REGISTER OTHER MODELS
# ========================================

# Inlines for User: show student uploads (PDFs, topics, subjects) for approval
class UserUploadedPDFInlineForm(forms.ModelForm):
    """Validate subject exists to prevent FOREIGN KEY constraint on save."""
    class Meta:
        model = PDFFile
        fields = ['title', 'subject', 'year', 'is_approved']

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if subject and not Subject.objects.filter(pk=subject.pk).exists():
            raise forms.ValidationError('Selected subject no longer exists. Edit this PDF from the PDF list to fix.')
        return subject


class UserUploadedPDFInline(admin.TabularInline):
    model = PDFFile
    form = UserUploadedPDFInlineForm
    fk_name = 'uploaded_by'
    extra = 0
    max_num = 0
    can_delete = True
    show_change_link = True
    fields = ['title', 'subject', 'year', 'is_approved', 'created_at']
    readonly_fields = ['title', 'subject', 'year', 'created_at']
    verbose_name = 'Uploaded PDF'
    verbose_name_plural = 'Uploaded PDFs (approve here or via PDF list)'


class UserUploadedSubjectInlineForm(forms.ModelForm):
    """Validate topic exists to prevent FOREIGN KEY constraint on save."""
    class Meta:
        model = Subject
        fields = ['name', 'topic', 'is_approved']

    def clean_topic(self):
        topic = self.cleaned_data.get('topic')
        if topic and not Topic.objects.filter(pk=topic.pk).exists():
            raise forms.ValidationError('Selected topic no longer exists. Edit this subject from the Subject list to fix.')
        return topic


class UserUploadedTopicInline(admin.TabularInline):
    model = Topic
    fk_name = 'uploaded_by'
    extra = 0
    max_num = 0
    can_delete = True
    show_change_link = True
    fields = ['name', 'is_approved', 'created_at']
    readonly_fields = ['created_at']
    verbose_name = 'Suggested Topic'
    verbose_name_plural = 'Suggested Topics (approve here or via Topic list)'


class UserUploadedSubjectInline(admin.TabularInline):
    model = Subject
    form = UserUploadedSubjectInlineForm
    fk_name = 'uploaded_by'
    extra = 0
    max_num = 0
    can_delete = True
    show_change_link = True
    fields = ['name', 'topic', 'is_approved', 'created_at']
    readonly_fields = ['created_at']
    verbose_name = 'Suggested Subject'
    verbose_name_plural = 'Suggested Subjects (approve here or via Subject list)'


# User Admin (custom) – shows all student uploads for approval
class CustomUserAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    list_display = ['phone', 'name', 'referral_code', 'is_active', 'uploaded_pdfs_count', 'uploaded_pending_count', 'created_at']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['phone', 'name', 'referral_code']
    readonly_fields = ['referral_code', 'created_at', 'last_login']
    inlines = [UserUploadedPDFInline, UserUploadedTopicInline, UserUploadedSubjectInline]

    def uploaded_pdfs_count(self, obj):
        return obj.uploaded_pdfs.count()
    uploaded_pdfs_count.short_description = 'PDFs uploaded'

    def uploaded_pending_count(self, obj):
        pending = obj.uploaded_pdfs.filter(is_approved=False).count()
        pending += obj.uploaded_topics.filter(is_approved=False).count()
        pending += obj.uploaded_subjects.filter(is_approved=False).count()
        return pending
    uploaded_pending_count.short_description = 'Pending approval'


admin.site.register(User, CustomUserAdmin)

# ========================================
# PDF FILE ADMIN (Premium / Lock control)
# ========================================

class PDFFileAdminForm(forms.ModelForm):
    """Auto-set is_premium / price based on pdf_type (Solution or Question+Solution → premium Rs 15)."""
    class Meta:
        model = PDFFile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and getattr(instance, 'pdf_type', 'QUESTION') in ('SOLUTION', 'BOTH'):
            self.initial['is_premium'] = True
            self.initial['price'] = Decimal('15.00')

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject:
            raise forms.ValidationError('Subject is required. Create a Topic and Subject first (PDF app → Topics → Subjects).')
        if not Subject.objects.filter(pk=subject.pk).exists():
            raise forms.ValidationError('Selected subject no longer exists. Please choose another.')
        return subject

    def clean_uploaded_by(self):
        uploaded_by = self.cleaned_data.get('uploaded_by')
        if uploaded_by and not User.objects.filter(pk=uploaded_by.pk).exists():
            raise forms.ValidationError('Selected user no longer exists. Leave empty or choose another.')
        return uploaded_by

    def clean(self):
        data = super().clean()
        pdf_type = data.get('pdf_type', 'QUESTION')
        if pdf_type in ('SOLUTION', 'BOTH'):
            data['is_solution'] = True
            data['is_premium'] = True
            data['price'] = Decimal('15.00')
        elif pdf_type == 'QUESTION':
            data['is_solution'] = False
        return data


class StudentUploadListFilter(admin.SimpleListFilter):
    title = 'student upload'
    parameter_name = 'student_upload'

    def lookups(self, request, model_admin):
        return (('yes', 'Student uploaded'), ('no', 'Admin only'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(uploaded_by__isnull=False)
        if self.value() == 'no':
            return queryset.filter(uploaded_by__isnull=True)
        return queryset


def _cascade_pdf_approval_to_subject_topic(pdf, is_approved):
    """When admin approves/rejects a student PDF, also approve/reject its subject and topic."""
    if not pdf.subject_id:
        return
    try:
        subject = pdf.subject
    except Subject.DoesNotExist:
        return  # Orphaned PDF (subject deleted)
    try:
        subject.is_approved = is_approved
        subject.save(update_fields=['is_approved'])
        if subject.topic_id:
            topic = subject.topic
            topic.is_approved = is_approved
            topic.save(update_fields=['is_approved'])
    except (IntegrityError, ObjectDoesNotExist):
        pass  # Skip cascade if subject/topic has FK issues


@admin.register(PDFFile)
class PDFFileAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    """Admin for PDF files. Student uploads need approval here; approve/reject PDF → subject & topic follow."""
    form = PDFFileAdminForm
    change_list_template = 'admin/pdf_app/pdffile/change_list.html'

    list_display = [
        'title',
        'subject',
        'year',
        'pdf_type',
        'is_premium',
        'price_display',
        'premium_badge',
        'uploaded_by_display',
        'is_approved',
        'created_at',
    ]
    
    list_filter = [StudentUploadListFilter, 'is_approved', 'subject', 'year', 'pdf_type', 'is_premium']
    
    search_fields = ['title', 'subtitle', 'subject__name', 'uploaded_by__phone', 'uploaded_by__name']
    
    list_editable = ['pdf_type', 'is_premium', 'is_approved']
    
    actions = ['approve_pdfs', 'reject_pdfs']

    fieldsets = (
        (None, {
            'fields': ('title', 'subtitle', 'year', 'subject', 'file'),
        }),
        ('Content Type & Premium', {
            'fields': ('pdf_type', 'is_premium', 'price'),
            'description': (
                'Question = Questions tab only. Solution = Solutions tab only (premium Rs 15 auto-set). '
                'Question + Solution = appears in BOTH tabs (premium Rs 15 auto-set). '
                'For plain Question PDFs you can tick Is Premium and set a custom price to lock them.'
            ),
        }),
        ('Student Upload', {
            'fields': ('uploaded_by', 'is_approved'),
            'description': (
                'Student uploads are free PDFs. Approve PDF → its subject and topic are auto-approved. '
                'Reject PDF → its subject and topic are auto-rejected.'
            ),
        }),
    )

    def uploaded_by_display(self, obj):
        if not obj.uploaded_by:
            return '—'
        u = obj.uploaded_by
        return f'{getattr(u, "name", "") or u.phone} ({u.phone})'
    uploaded_by_display.short_description = 'Uploaded by'

    def get_integrity_error_message(self, exc, context='save'):
        return (
            'Foreign key constraint failed. The Subject or Uploaded-by user may have been deleted. '
            'Select a valid Subject and ensure Uploaded-by (if set) exists. '
            f'Details: {exc}'
        )

    def save_model(self, request, obj, form, change):
        # Ensure subject exists before cascade (fix orphaned PDFs)
        if obj.subject_id and not Subject.objects.filter(pk=obj.subject_id).exists():
            messages.error(
                request,
                f'PDF references deleted Subject (id={obj.subject_id}). Please select a valid Subject.'
            )
            raise ValueError('Subject no longer exists. Select a valid Subject.')
        if obj.uploaded_by_id and not User.objects.filter(pk=obj.uploaded_by_id).exists():
            obj.uploaded_by_id = None  # Clear orphaned user ref
        if change and obj.uploaded_by_id and obj.pk:
            try:
                old = PDFFile.objects.get(pk=obj.pk)
                if old.is_approved != obj.is_approved:
                    _cascade_pdf_approval_to_subject_topic(obj, obj.is_approved)
            except PDFFile.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)

    @admin.action(description='Approve selected PDFs')
    def approve_pdfs(self, request, queryset):
        for pdf in queryset.filter(uploaded_by__isnull=False):
            _cascade_pdf_approval_to_subject_topic(pdf, True)
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} PDF(s) approved (subject & topic auto-approved where applicable).')

    @admin.action(description='Reject selected PDFs')
    def reject_pdfs(self, request, queryset):
        for pdf in queryset.filter(uploaded_by__isnull=False):
            _cascade_pdf_approval_to_subject_topic(pdf, False)
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} PDF(s) rejected (subject & topic auto-rejected where applicable).')
    
    def premium_badge(self, obj):
        """Show Premium badge if locked"""
        if obj.is_premium or obj.pdf_type in ('SOLUTION', 'BOTH'):
            return format_html(
                '<span style="background:#FFD700; color:#333; padding:4px 8px; border-radius:4px; font-weight:bold;">🔒 PREMIUM</span>'
            )
        return format_html('<span style="color:#28a745;">✓ Free</span>')
    premium_badge.short_description = 'Status'
    
    def price_display(self, obj):
        if obj.is_premium or obj.pdf_type in ('SOLUTION', 'BOTH'):
            return f'₹{obj.price}' if obj.price else 'Subscription'
        return '-'
    price_display.short_description = 'Price'


# ========================================
# TOPIC & SUBJECT ADMIN (student-created, approval)
# ========================================

@admin.register(Topic)
class TopicAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'uploaded_by_display', 'is_approved', 'created_at']
    list_filter = ['is_approved']
    search_fields = ['name', 'uploaded_by__phone', 'uploaded_by__name']
    list_editable = ['is_approved']
    actions = ['approve_topics', 'reject_topics']

    def uploaded_by_display(self, obj):
        if not obj.uploaded_by:
            return '—'
        u = obj.uploaded_by
        return f'{getattr(u, "name", "") or u.phone} ({u.phone})'
    uploaded_by_display.short_description = 'Uploaded by'

    @admin.action(description='Approve selected topics')
    def approve_topics(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} topic(s) approved.')

    @admin.action(description='Reject selected topics')
    def reject_topics(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} topic(s) rejected.')


@admin.register(Subject)
class SubjectAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    list_display = ['id', 'name', 'topic', 'uploaded_by_display', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'topic']
    search_fields = ['name', 'topic__name', 'uploaded_by__phone', 'uploaded_by__name']
    list_editable = ['is_approved']
    actions = ['approve_subjects', 'reject_subjects']

    def uploaded_by_display(self, obj):
        if not obj.uploaded_by:
            return '—'
        u = obj.uploaded_by
        return f'{getattr(u, "name", "") or u.phone} ({u.phone})'
    uploaded_by_display.short_description = 'Uploaded by'

    @admin.action(description='Approve selected subjects')
    def approve_subjects(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} subject(s) approved.')

    @admin.action(description='Reject selected subjects')
    def reject_subjects(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} subject(s) rejected.')


# Simple registrations
admin.site.register(Feedback)
admin.site.register(UserQuery)


@admin.register(PdfAccess)
class PdfAccessAdmin(admin.ModelAdmin):
    """PDF access (also visible as inline on each Payment)."""
    list_display = ['id', 'user_phone', 'pdf_title', 'payment_link', 'granted_at']
    list_filter = ['granted_at']
    search_fields = ['user__phone', 'pdf__title']
    readonly_fields = ['user', 'pdf', 'payment', 'granted_at']
    raw_id_fields = ['user', 'pdf', 'payment']

    def user_phone(self, obj):
        return obj.user.phone if obj.user else '-'
    user_phone.short_description = 'User'

    def pdf_title(self, obj):
        return obj.pdf.title if obj.pdf else '-'
    pdf_title.short_description = 'PDF'

    def payment_link(self, obj):
        if obj.payment_id:
            url = reverse('admin:pdf_app_payment_change', args=[obj.payment_id])
            label = str(obj.payment.payment_id)[:8] if obj.payment else str(obj.payment_id)
            return format_html('<a href="{}">{}</a>', url, label)
        return '-'
    payment_link.short_description = 'Payment'


admin.site.register(MessageQuota)
admin.site.register(Referral)
admin.site.register(ReferralReward)
admin.site.register(UserStreak)
admin.site.register(UserBookmark)
admin.site.register(UserActivity)


# ========================================
# NOTIFICATIONS (send to all users; user can pin / save for later)
# ========================================

class NotificationAdminForm(forms.ModelForm):
    """Add option to send one notification to all users."""
    send_to_all = forms.BooleanField(
        required=False,
        initial=False,
        label='Send to all users',
        help_text='If checked, this notification will be created for every active user (user field is ignored).',
    )

    class Meta:
        model = Notification
        fields = ['user', 'title', 'body', 'subject', 'action_url']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False
        if self.instance and self.instance.pk:
            self.fields['send_to_all'].widget = forms.HiddenInput()


@admin.register(Notification)
class NotificationAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    form = NotificationAdminForm
    list_display = ['id', 'title_short', 'user', 'subject', 'is_read', 'is_pinned', 'created_at']
    list_filter = ['is_read', 'is_pinned', 'subject', 'created_at']
    search_fields = ['title', 'body', 'user__phone']
    raw_id_fields = ['user', 'subject']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {'fields': ('user', 'send_to_all', 'title', 'body', 'subject', 'action_url')}),
            )
        return super().get_fieldsets(request, obj)

    def title_short(self, obj):
        return (obj.title[:50] + '...') if obj.title and len(obj.title) > 50 else (obj.title or '-')
    title_short.short_description = 'Title'

    def save_model(self, request, obj, form, change):
        if not change and form.cleaned_data.get('send_to_all'):
            users = User.objects.filter(is_active=True)
            count = 0
            for u in users:
                Notification.objects.create(
                    user=u,
                    title=obj.title,
                    body=obj.body or '',
                    subject=obj.subject,
                    action_url=obj.action_url or '',
                )
                count += 1
            self.message_user(request, f'Created {count} notifications for all users.', messages.SUCCESS)
            return
        if not obj.user_id and not form.cleaned_data.get('send_to_all'):
            self.message_user(request, 'Either select a user or check "Send to all users".', messages.ERROR)
            return
        super().save_model(request, obj, form, change)


# ========================================
# SUBJECT ROUTINE (per-subject schedule; user can start reminder)
# ========================================

@admin.register(SubjectRoutine)
class SubjectRoutineAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    list_display = ['id', 'subject', 'day_of_week', 'start_time', 'end_time', 'title', 'order']
    list_filter = ['subject', 'day_of_week']
    search_fields = ['title', 'description', 'subject__name']
    list_editable = ['order']


@admin.register(UserRoutineReminder)
class UserRoutineReminderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone', 'routine_display', 'notify_minutes_before', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone', 'routine__title']
    raw_id_fields = ['user', 'routine']

    def user_phone(self, obj):
        return obj.user.phone if obj.user else '-'
    user_phone.short_description = 'User'

    def routine_display(self, obj):
        if obj.routine:
            return f'{obj.routine.subject.name} – {obj.routine.get_day_of_week_display()} {obj.routine.start_time}'
        return '-'
    routine_display.short_description = 'Routine'


# ========================================
# FEED POST (image, title, description; user can like)
# ========================================

@admin.register(FeedPost)
class FeedPostAdmin(IntegrityErrorMixin, admin.ModelAdmin):
    list_display = ['id', 'image_preview', 'title_short', 'like_count_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']

    def image_preview(self, obj):
        if obj and obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-width:80px;height:auto;border-radius:6px;"/>',
                obj.image.url
            )
        return '–'
    image_preview.short_description = 'Image'

    def title_short(self, obj):
        return (obj.title[:40] + '...') if obj.title and len(obj.title) > 40 else (obj.title or '–')
    title_short.short_description = 'Title'

    def like_count_display(self, obj):
        return obj.likes.count() if obj.pk else 0
    like_count_display.short_description = 'Likes'


@admin.register(FeedPostLike)
class FeedPostLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone', 'post_title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone', 'post__title']
    raw_id_fields = ['user', 'post']

    def user_phone(self, obj):
        return obj.user.phone if obj.user else '–'
    user_phone.short_description = 'User'

    def post_title(self, obj):
        return (obj.post.title[:50] + '...') if obj.post and len(obj.post.title) > 50 else (obj.post.title if obj.post else '–')
    post_title.short_description = 'Post'


# ========================================
# ADMIN SITE CUSTOMIZATION
# ========================================

admin.site.site_header = "Bachelor Question Bank Admin"
admin.site.site_title = "BQB Admin Portal"
admin.site.index_title = "Welcome to Bachelor Question Bank Administration"