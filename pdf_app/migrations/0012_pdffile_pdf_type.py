# Add pdf_type field to PDFFile: QUESTION / SOLUTION / BOTH
# Data migration: backfill from existing is_solution boolean

from django.db import migrations, models


def backfill_pdf_type(apps, schema_editor):
    """Set pdf_type based on existing is_solution field."""
    PDFFile = apps.get_model('pdf_app', 'PDFFile')
    PDFFile.objects.filter(is_solution=True).update(pdf_type='SOLUTION')
    # QUESTION is the default, so is_solution=False records are already correct.


def reverse_backfill(apps, schema_editor):
    """Reverse: set all to QUESTION (no-op since is_solution still exists)."""
    PDFFile = apps.get_model('pdf_app', 'PDFFile')
    PDFFile.objects.all().update(pdf_type='QUESTION')


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0011_pdfpackage_topic'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdffile',
            name='pdf_type',
            field=models.CharField(
                choices=[
                    ('QUESTION', 'Question'),
                    ('SOLUTION', 'Solution'),
                    ('BOTH', 'Question + Solution'),
                ],
                default='QUESTION',
                help_text=(
                    'Question = Questions tab only. Solution = Solutions tab only. '
                    'Question + Solution = both tabs, always premium.'
                ),
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_pdf_type, reverse_backfill),
    ]
