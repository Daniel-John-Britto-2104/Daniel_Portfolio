from django.db import migrations
from website.portfolio_defaults import seed_database_tables


def seed_portfolio_data(apps, schema_editor):
    seed_database_tables(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0003_update_profile_email"),
    ]

    operations = [
        migrations.RunPython(seed_portfolio_data, migrations.RunPython.noop),
    ]
