from django.contrib import admin
from django.utils.html import format_html
from .models import Topic, Subject, PDFFile
from django.urls import reverse

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject_count']
    search_fields = ['name']
    
    def subject_count(self, obj):
        count = obj.subjects.count()
        url = reverse('admin:pdf_app_subject_changelist') + f'?topic__id__exact={obj.id}'
        return format_html('<a href="{}">{} Subjects</a>', url, count)
    subject_count.short_description = 'Subjects'

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic_link', 'pdf_count']
    list_filter = ['topic']
    search_fields = ['name']
    
    def topic_link(self, obj):
        url = reverse('admin:pdf_app_topic_change', args=[obj.topic.id])
        return format_html('<a href="{}">{}</a>', url, obj.topic.name)
    topic_link.short_description = 'Topic'
    
    def pdf_count(self, obj):
        count = obj.pdfs.count()
        url = reverse('admin:pdf_app_pdffile_changelist') + f'?subject__id__exact={obj.id}'
        return format_html('<a href="{}">{} PDFs</a>', url, count)
    pdf_count.short_description = 'PDFs'

@admin.register(PDFFile)
class PDFFileAdmin(admin.ModelAdmin):
    list_display = ['title', 'year', 'subject_link', 'file_link']
    list_filter = ['year', 'subject__topic', 'subject']
    search_fields = ['title', 'subject__name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'subtitle', 'year')
        }),
        ('Relationships', {
            'fields': ('subject', 'file')
        }),
    )
    
    def subject_link(self, obj):
        url = reverse('admin:pdf_app_subject_change', args=[obj.subject.id])
        return format_html('<a href="{}">{}</a>', url, obj.subject.name)
    subject_link.short_description = 'Subject'
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.file.url)
        return "-"
    file_link.short_description = 'File'