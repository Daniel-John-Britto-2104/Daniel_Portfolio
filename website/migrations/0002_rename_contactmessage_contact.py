from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ContactMessage",
            new_name="Contact",
        ),
        migrations.AlterField(
            model_name="contact",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="contact",
            name="subject",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterModelOptions(
            name="contact",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Contact",
                "verbose_name_plural": "Contacts",
            },
        ),
    ]
