from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import SolutionTopic, SolutionSubject, SolutionPDFFile, SolutionFeedback

@admin.register(SolutionTopic)
class SolutionTopicAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(SolutionSubject)
class SolutionSubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic']

@admin.register(SolutionPDFFile)
class SolutionPDFFileAdmin(admin.ModelAdmin):
    list_display = ['title', 'year', 'subject', 'is_question', 'file_link']
    list_editable = ['is_question']
    list_filter = ['year', 'subject', 'is_question']
    search_fields = ['title', 'subject__name']

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.file.url)
        return "-"
    file_link.short_description = 'PDF File'

@admin.register(SolutionFeedback)
class SolutionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
