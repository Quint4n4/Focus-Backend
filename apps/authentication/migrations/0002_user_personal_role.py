from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('admin_area', 'Admin de Área'),
                    ('trabajador', 'Trabajador de Área'),
                    ('personal', 'Personal'),
                ],
                default='trabajador',
                max_length=20,
            ),
        ),
    ]
