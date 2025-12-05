from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        # 1. Drop the default Primary Key constraint (which is just on 'id')
        migrations.RunSQL(
            sql="ALTER TABLE dashboard_dmarcreport DROP CONSTRAINT dashboard_dmarcreport_pkey;",
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # 2. Create a new Composite Primary Key that includes the partition column (date_begin)
        # TimescaleDB requires this structure.
        migrations.RunSQL(
            sql="ALTER TABLE dashboard_dmarcreport ADD PRIMARY KEY (id, date_begin);",
            reverse_sql=migrations.RunSQL.noop
        ),

        # 3. Convert the table into a Hypertable
        migrations.RunSQL(
            sql="SELECT create_hypertable('dashboard_dmarcreport', 'date_begin', migrate_data => true);",
            reverse_sql="SELECT 1;"
        ),
    ]