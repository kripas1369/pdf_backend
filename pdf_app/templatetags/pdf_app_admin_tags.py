from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def pending_student_pdfs_count():
    """Count of PDFs uploaded by students that are pending approval (not yet approved)."""
    from pdf_app.models import PDFFile
    return PDFFile.objects.filter(uploaded_by__isnull=False, is_approved=False).count()
