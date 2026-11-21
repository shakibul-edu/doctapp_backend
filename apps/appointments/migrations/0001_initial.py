import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("doctors", "0001_initial"),
        ("hospitals", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS btree_gist;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="AvailabilitySchedule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("appointment_duration_minutes", models.PositiveSmallIntegerField(default=30)),
                ("break_start", models.TimeField(blank=True, null=True)),
                ("break_end", models.TimeField(blank=True, null=True)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chamber", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_schedules", to="hospitals.chamber")),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_schedules", to="doctors.doctorprofile")),
            ],
            options={
                "ordering": ["weekday", "start_time"],
                "constraints": [
                    models.UniqueConstraint(fields=("doctor", "chamber", "weekday", "start_time"), name="unique_doctor_chamber_weekday_schedule"),
                    models.CheckConstraint(condition=models.Q(("end_time__gt", models.F("start_time"))), name="schedule_end_after_start"),
                    models.CheckConstraint(condition=models.Q(("appointment_duration_minutes__gt", 0)), name="schedule_positive_duration"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ScheduleException",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("exception_type", models.CharField(choices=[("LEAVE", "Leave"), ("HOLIDAY", "Holiday"), ("TEMPORARY_UNAVAILABLE", "Temporary unavailable"), ("MODIFIED_HOURS", "Modified working hours"), ("ONE_TIME", "One-time schedule change")], max_length=32)),
                ("date", models.DateField(db_index=True)),
                ("start_datetime", models.DateTimeField(blank=True, null=True)),
                ("end_datetime", models.DateTimeField(blank=True, null=True)),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                ("break_start", models.TimeField(blank=True, null=True)),
                ("break_end", models.TimeField(blank=True, null=True)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chamber", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="schedule_exceptions", to="hospitals.chamber")),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedule_exceptions", to="doctors.doctorprofile")),
            ],
            options={"ordering": ["date", "start_datetime", "start_time"]},
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_at", models.DateTimeField(db_index=True)),
                ("end_at", models.DateTimeField(db_index=True)),
                ("consultation_fee_snapshot", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled"), ("COMPLETED", "Completed"), ("NO_SHOW", "No show")], db_index=True, default="PENDING", max_length=20)),
                ("patient_notes", models.TextField(blank=True)),
                ("cancellation_reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chamber", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="hospitals.chamber")),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="doctors.doctorprofile")),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-start_at"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("end_at__gt", models.F("start_at"))), name="appointment_end_after_start"),
                ],
            },
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE appointments_appointment
            ADD CONSTRAINT appointment_no_active_overlap
            EXCLUDE USING gist (
                doctor_id WITH =,
                tstzrange(start_at, end_at, '[)') WITH &&
            )
            WHERE (status IN ('PENDING', 'CONFIRMED'));
            """,
            reverse_sql="ALTER TABLE appointments_appointment DROP CONSTRAINT IF EXISTS appointment_no_active_overlap;",
        ),
    ]
