# Generated migration: add last_seen to User for active-online presence

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0021_feedback_add_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_seen',
            field=models.DateTimeField(blank=True, help_text='Updated by app heartbeat; used for active-online count.', null=True),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['last_seen'], name='users_last_s_idx'),
        ),
    ]
