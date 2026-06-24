from django.db import migrations


def assign_default_company(apps, schema_editor):
    Company    = apps.get_model('companies',     'Company')
    User       = apps.get_model('authentication','User')
    Area       = apps.get_model('areas',         'Area')
    Project    = apps.get_model('projects',      'Project')
    Activity   = apps.get_model('activities',    'Activity')
    Invitation = apps.get_model('users',         'Invitation')

    company, _ = Company.objects.get_or_create(
        slug='default',
        defaults={'name': 'Default'},
    )

    for Model in (User, Area, Project, Activity, Invitation):
        Model.objects.filter(company__isnull=True).update(company=company)


def reverse_assign(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    Company.objects.filter(slug='default').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('companies',     '0001_initial'),
        ('authentication','0003_add_company_fk'),
        ('areas',         '0003_add_company_fk'),
        ('projects',      '0003_add_company_fk'),
        ('activities',    '0003_add_company_fk'),
        ('users',         '0004_add_company_fk'),
    ]

    operations = [
        migrations.RunPython(assign_default_company, reverse_code=reverse_assign),
    ]
