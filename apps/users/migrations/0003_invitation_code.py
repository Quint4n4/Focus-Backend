from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_invitation_area_alter_invitation_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='code',
            field=models.CharField(blank=True, max_length=16, null=True, unique=True),
        ),
    ]
