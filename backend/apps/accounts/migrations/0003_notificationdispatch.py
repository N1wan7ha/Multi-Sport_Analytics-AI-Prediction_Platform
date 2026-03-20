from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
        ('predictions', '0001_initial'),
        ('accounts', '0002_userfavouriteteam'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationDispatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('match_start', 'Match Start'), ('prediction_ready', 'Prediction Ready')], max_length=30)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('match', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='matches.match')),
                ('prediction_job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='predictions.predictionjob')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_dispatches', to='accounts.user')),
            ],
            options={
                'db_table': 'notification_dispatches',
            },
        ),
        migrations.AddIndex(
            model_name='notificationdispatch',
            index=models.Index(fields=['notification_type', 'sent_at'], name='notificatio_notific_6ec1cf_idx'),
        ),
    ]
