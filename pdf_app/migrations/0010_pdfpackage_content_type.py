# Add content_type to PDFPackage (All / Questions only / Solutions only)

from django.db import migrations, models


def set_content_type_from_solution_package(apps, schema_editor):
    PDFPackage = apps.get_model('pdf_app', 'PDFPackage')
    for pkg in PDFPackage.objects.all():
        if getattr(pkg, 'is_solution_package', False):
            pkg.content_type = 'SOLUTIONS'
        else:
            pkg.content_type = 'ALL'
        pkg.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0009_merge_20260212_2243'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfpackage',
            name='content_type',
            field=models.CharField(
                choices=[('ALL', 'All PDFs (questions + solutions)'), ('QUESTIONS', 'Questions only'), ('SOLUTIONS', 'Solutions only')],
                default='ALL',
                help_text='Which PDFs to include: All, Questions only, or Solutions only.',
                max_length=20,
            ),
        ),
        migrations.RunPython(set_content_type_from_solution_package, migrations.RunPython.noop),
    ]
