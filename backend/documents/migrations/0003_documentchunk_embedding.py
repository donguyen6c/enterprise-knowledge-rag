from django.db import migrations
from pgvector.django import VectorExtension, VectorField


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_documentchunk"),
    ]

    operations = [
        VectorExtension(),

        migrations.AddField(
            model_name="documentchunk",
            name="embedding",
            field=VectorField( dimensions=384, null=True, blank=True,),
        ),
    ]