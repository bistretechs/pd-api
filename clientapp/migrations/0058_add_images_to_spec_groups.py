from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientapp', '0057_printcategory_remove_process_created_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productspecgroup',
            name='header_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='spec_groups/headers/%Y/%m/',
                help_text='Illustrative diagram or image shown above the group on the storefront',
            ),
        ),
        migrations.AddField(
            model_name='specgrouplibraryoption',
            name='preview_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='spec_groups/library_options/%Y/%m/',
                help_text='Swatch or preview image shown on the storefront',
            ),
        ),
        migrations.AddField(
            model_name='specoption',
            name='preview_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='spec_groups/options/%Y/%m/',
                help_text='Swatch or preview image shown on the storefront for this option',
            ),
        ),
    ]
