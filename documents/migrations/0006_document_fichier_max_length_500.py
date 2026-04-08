from django.db import migrations, models
import documents.models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_fix_versiondocument_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='fichier',
            field=models.FileField(
                blank=True,
                help_text='Fichier stocké dans S3/MinIO',
                max_length=500,
                null=True,
                storage=documents.models.DocumentStorage(),
                upload_to=documents.models.document_upload_path,
                verbose_name='Fichier',
            ),
        ),
    ]
