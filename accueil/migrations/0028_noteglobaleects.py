# Generated by Django 4.1 on 2023-06-07 23:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accueil', '0027_config_ects_modif'),
    ]

    operations = [
        migrations.CreateModel(
            name='NoteGlobaleECTS',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annee', models.PositiveSmallIntegerField(choices=[(1, '1ère année'), (2, '2ème année')], verbose_name='année')),
                ('note', models.PositiveSmallIntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D'), (4, 'E'), (5, 'F')])),
                ('eleve', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accueil.eleve', verbose_name='Élève')),
            ],
        ),
    ]
