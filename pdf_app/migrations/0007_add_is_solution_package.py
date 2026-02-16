# Add is_solution_package to PDFPackage (for "Year X Solutions" bulk option)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0006_ensure_users_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfpackage',
            name='is_solution_package',
            field=models.BooleanField(
                default=False,
                help_text='If True, this package is for solutions only (e.g. "Year 2080 Solutions"). App shows "Buy all solutions for this year".'
            ),
        ),
    ]
