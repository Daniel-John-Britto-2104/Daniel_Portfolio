from django.db import migrations, models


OLD_EMAILS = (
    "danielamalraj309@gmail.com",
    "danieljohnbritto@gmail.com",
)
NEW_EMAIL = "danieljohnbrittoaj@gmail.com"


def update_email_addresses(apps, schema_editor):
    Profile = apps.get_model("website", "Profile")
    SocialLink = apps.get_model("website", "SocialLink")

    Profile.objects.filter(email__in=OLD_EMAILS).update(email=NEW_EMAIL)
    SocialLink.objects.filter(url="mailto:danielamalraj309@gmail.com").update(
        url=f"mailto:{NEW_EMAIL}"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0002_rename_contactmessage_contact"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="email",
            field=models.EmailField(default=NEW_EMAIL, max_length=254),
        ),
        migrations.RunPython(update_email_addresses, migrations.RunPython.noop),
    ]
