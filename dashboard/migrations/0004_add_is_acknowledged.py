from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_dmarcreport_report_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='dmarcreport',
            name='is_acknowledged',
            field=models.BooleanField(default=False, help_text='Has this threat been manually reviewed?'),
        ),
    ]