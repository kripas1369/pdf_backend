# Set is_premium=True and price=15 for all existing PDFs where is_solution=True

from decimal import Decimal
from django.db import migrations


def set_solution_premium_and_price(apps, schema_editor):
    PDFFile = apps.get_model('pdf_app', 'PDFFile')
    PDFFile.objects.filter(is_solution=True).update(is_premium=True, price=Decimal('15.00'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0007_add_is_solution_package'),
    ]

    operations = [
        migrations.RunPython(set_solution_premium_and_price, noop),
    ]
