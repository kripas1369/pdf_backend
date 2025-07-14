from django import forms
from .models import SolutionSubject

class MultipleSolutionPDFInput(forms.FileInput):
    def __init__(self, attrs=None):
        default_attrs = {'multiple': True, 'accept': '.pdf'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class BulkSolutionPDFUploadForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=SolutionSubject.objects.all())
    year = forms.IntegerField(min_value=2000, max_value=2100)
    pdf_files = forms.FileField(widget=MultipleSolutionPDFInput())
