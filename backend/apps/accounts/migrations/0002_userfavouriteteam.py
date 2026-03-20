from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFavouriteTeam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favoured_by_users', to='matches.team')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favourite_teams', to='accounts.user')),
            ],
            options={
                'db_table': 'user_favourite_teams',
                'unique_together': {('user', 'team')},
            },
        ),
    ]
