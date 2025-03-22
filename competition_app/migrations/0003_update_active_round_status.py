from django.db import migrations

def update_active_round_status(apps, schema_editor):
    Round = apps.get_model('competition_app', 'Round')
    # Update any rounds with 'ACTIVE' status to 'ONGOING'
    Round.objects.filter(status='ACTIVE').update(status='ONGOING')

class Migration(migrations.Migration):
    dependencies = [
        ('competition_app', '0002_alter_participant_options_and_more'),
    ]

    operations = [
        migrations.RunPython(update_active_round_status),
    ]
