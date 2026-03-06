from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clientapp', '0054_jobfile_documentshare_deadlinealert_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vendor',
            name='vps_score',
        ),
    ]
