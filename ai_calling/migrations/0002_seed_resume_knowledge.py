from django.db import migrations


def seed_resume_chunks(apps, schema_editor):
    ResumeKnowledgeChunk = apps.get_model("ai_calling", "ResumeKnowledgeChunk")
    if ResumeKnowledgeChunk.objects.exists():
        return

    from ai_calling.management.commands.load_resume_knowledge import VERIFIED_RESUME_CHUNKS

    for item in VERIFIED_RESUME_CHUNKS:
        ResumeKnowledgeChunk.objects.create(
            chunk_id=item["chunk_id"],
            category=item["category"],
            title=item["title"],
            content=item["content"],
            embedding=[],
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("ai_calling", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_resume_chunks, migrations.RunPython.noop),
    ]
