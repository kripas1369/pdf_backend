# Create users table if missing (old production DB may have migration state but no table)

from django.db import migrations


def create_users_table_if_missing(apps, schema_editor):
    """Create users table if it does not exist (fix old production DB)."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        )
        if cursor.fetchone():
            return
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "users" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "password" varchar(128) NOT NULL,
                "last_login" datetime NULL,
                "is_superuser" bool NOT NULL DEFAULT 0,
                "phone" varchar(15) NOT NULL UNIQUE,
                "name" varchar(100) NOT NULL DEFAULT '',
                "first_opened_at" datetime NULL,
                "pdf_views_count" integer NOT NULL DEFAULT 0,
                "days_since_install" integer NOT NULL DEFAULT 0,
                "referral_code" varchar(20) NOT NULL DEFAULT '',
                "is_active" bool NOT NULL DEFAULT 1,
                "is_staff" bool NOT NULL DEFAULT 0,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL,
                "referred_by_id" integer NULL REFERENCES "users" ("id") ON DELETE SET NULL
            )
        """)
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "users_phone_af6883_idx" ON "users" ("phone")'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "users_referra_98b351_idx" ON "users" ("referral_code")'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_app', '0005_add_full_package_type'),
    ]

    operations = [
        migrations.RunPython(create_users_table_if_missing, migrations.RunPython.noop),
    ]
