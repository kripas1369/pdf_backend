# Add Topic package: topic FK on PDFPackage (all subjects under one topic)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0010_pdfpackage_content_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfpackage',
            name='topic',
            field=models.ForeignKey(
                blank=True,
                help_text='For Topic package: select the topic (all subjects under it). Leave empty for Subject/Year.',
                null=True,
                on_delete=models.CASCADE,
                related_name='packages',
                to='pdf_app.topic',
            ),
        ),
    ]
