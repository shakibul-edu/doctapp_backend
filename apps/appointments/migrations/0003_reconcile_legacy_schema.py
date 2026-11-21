from django.db import migrations


def reconcile_legacy_appointment_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN (
                  'appointments_scheduleexception',
                  'appointments_appointment'
              )
            """
        )
        columns = {(table, column) for table, column in cursor.fetchall()}

        if ("appointments_scheduleexception", "exception_date") in columns:
            cursor.execute(
                "ALTER TABLE appointments_scheduleexception "
                "RENAME COLUMN exception_date TO date"
            )

        cursor.execute(
            "ALTER TABLE appointments_scheduleexception "
            "ADD COLUMN IF NOT EXISTS start_datetime timestamp with time zone"
        )
        cursor.execute(
            "ALTER TABLE appointments_scheduleexception "
            "ADD COLUMN IF NOT EXISTS end_datetime timestamp with time zone"
        )
        cursor.execute(
            "ALTER TABLE appointments_scheduleexception "
            "ADD COLUMN IF NOT EXISTS break_start time"
        )
        cursor.execute(
            "ALTER TABLE appointments_scheduleexception "
            "ADD COLUMN IF NOT EXISTS break_end time"
        )

        if ("appointments_appointment", "start_datetime") in columns:
            cursor.execute(
                "ALTER TABLE appointments_appointment "
                "DROP CONSTRAINT IF EXISTS appointments_no_active_overlap"
            )
            cursor.execute(
                "ALTER TABLE appointments_appointment "
                "RENAME COLUMN start_datetime TO start_at"
            )
            cursor.execute(
                "ALTER TABLE appointments_appointment "
                "RENAME COLUMN end_datetime TO end_at"
            )

        cursor.execute(
            "ALTER TABLE appointments_appointment "
            "DROP CONSTRAINT IF EXISTS appointment_end_after_start"
        )
        cursor.execute(
            "ALTER TABLE appointments_appointment "
            "ADD CONSTRAINT appointment_end_after_start "
            "CHECK (end_at > start_at)"
        )

        cursor.execute(
            "ALTER TABLE appointments_appointment "
            "DROP CONSTRAINT IF EXISTS appointments_no_active_overlap"
        )
        cursor.execute(
            "ALTER TABLE appointments_appointment "
            "DROP CONSTRAINT IF EXISTS appointment_no_active_overlap"
        )
        cursor.execute(
            "ALTER TABLE appointments_appointment "
            "ADD CONSTRAINT appointment_no_active_overlap "
            "EXCLUDE USING gist ("
            "doctor_id WITH =,"
            "tstzrange(start_at, end_at, '[)') WITH &&"
            ") "
            "WHERE (status IN ('PENDING', 'CONFIRMED'))"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_legacy_appointment_schema,
            migrations.RunPython.noop,
        ),
    ]
