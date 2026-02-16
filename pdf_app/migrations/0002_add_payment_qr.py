# Generated manually for PaymentQR model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentQR',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qr_image', models.ImageField(help_text='QR code for payment - users scan this', upload_to='payment_qr/')),
                ('instructions', models.CharField(blank=True, help_text='e.g. Scan with eSewa, Khalti', max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Payment QR Code',
                'verbose_name_plural': 'Payment QR Code',
            },
        ),
    ]
