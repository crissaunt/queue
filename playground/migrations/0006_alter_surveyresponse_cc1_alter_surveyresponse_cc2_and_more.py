from django.db import migrations, models
import django.contrib.postgres.fields.jsonb

class Migration(migrations.Migration):

    dependencies = [
        ('playground', '0005_surveyresponse_delete_satisfactionsurvey'),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE playground_surveyresponse
            ALTER COLUMN cc1 TYPE jsonb
            USING to_jsonb(cc1),
            ALTER COLUMN cc2 TYPE jsonb
            USING to_jsonb(cc2),
            ALTER COLUMN cc3 TYPE jsonb
            USING to_jsonb(cc3);
            """
        ),
    ]
