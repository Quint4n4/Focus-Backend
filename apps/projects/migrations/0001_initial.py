import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Minimal placeholder migration for the Project model.
    The full Project model will be implemented in Phase 4.
    Activities depend on this migration to resolve the FK to projects.Project.
    """

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
