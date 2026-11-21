from datetime import datetime, timedelta, timezone as datetime_timezone

from django.db.models import Q
from django.utils import timezone

from apps.hospitals.models import Chamber

from .models import Appointment, AvailabilitySchedule, ScheduleException


def _exception_applies(exception, chamber_id):
    return exception.chamber_id is None or str(exception.chamber_id) == str(chamber_id)


def _combine(day, value):
    local = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(day, value), local)


def _overlaps(start_at, end_at, reserved_start, reserved_end):
    return start_at < reserved_end and end_at > reserved_start


def generate_available_slots(doctor, chamber=None, start_date=None, end_date=None):
    local_now = timezone.localtime()
    start_date = start_date or local_now.date()
    end_date = end_date or start_date
    if end_date < start_date:
        return []

    chambers = Chamber.objects.filter(
        doctor=doctor,
        active=True,
    )
    if chamber is not None:
        chambers = chambers.filter(pk=chamber.pk)

    reserved = Appointment.objects.filter(
        doctor=doctor,
        status__in=(Appointment.Status.PENDING, Appointment.Status.CONFIRMED),
        start_at__date__gte=start_date,
        start_at__date__lte=end_date,
    ).values("chamber_id", "start_at", "end_at")

    slots = []
    day = start_date
    while day <= end_date:
        weekday = day.weekday()
        exceptions = ScheduleException.objects.filter(
            doctor=doctor,
            date=day,
            active=True,
        )

        for chamber_obj in chambers:
            chamber_exceptions = [
                item for item in exceptions if _exception_applies(item, chamber_obj.id)
            ]
            if any(
                item.exception_type in (
                    ScheduleException.ExceptionType.LEAVE,
                    ScheduleException.ExceptionType.HOLIDAY,
                )
                for item in chamber_exceptions
            ):
                continue

            schedules = AvailabilitySchedule.objects.filter(
                doctor=doctor,
                chamber=chamber_obj,
                weekday=weekday,
                active=True,
            )

            override = next(
                (
                    item
                    for item in chamber_exceptions
                    if item.exception_type in (
                        ScheduleException.ExceptionType.MODIFIED_HOURS,
                        ScheduleException.ExceptionType.ONE_TIME,
                    )
                    and item.start_time is not None
                    and item.end_time is not None
                ),
                None,
            )

            periods = []
            if override is not None:
                matching_schedule = schedules.filter(
                    start_time__lte=override.start_time,
                    end_time__gte=override.end_time,
                ).first()
                periods.append(
                    (
                        override.start_time,
                        override.end_time,
                        override.break_start,
                        override.break_end,
                        matching_schedule.appointment_duration_minutes
                        if matching_schedule
                        else 30,
                    )
                )
            else:
                periods.extend(
                    (
                        schedule.start_time,
                        schedule.end_time,
                        schedule.break_start,
                        schedule.break_end,
                        schedule.appointment_duration_minutes,
                    )
                    for schedule in schedules
                )

            for start_time, end_time, break_start, break_end, duration in periods:
                period_start = _combine(day, start_time)
                period_end = _combine(day, end_time)
                cursor = period_start
                duration_delta = timedelta(minutes=duration)

                while cursor + duration_delta <= period_end:
                    slot_end = cursor + duration_delta
                    break_overlaps = (
                        break_start is not None
                        and break_end is not None
                        and _overlaps(
                            cursor,
                            slot_end,
                            _combine(day, break_start),
                            _combine(day, break_end),
                        )
                    )

                    unavailable = False
                    for exception in chamber_exceptions:
                        if exception.exception_type not in (
                            ScheduleException.ExceptionType.TEMPORARY_UNAVAILABLE,
                            ScheduleException.ExceptionType.ONE_TIME,
                        ):
                            continue
                        unavailable_start = exception.start_datetime
                        unavailable_end = exception.end_datetime
                        if unavailable_start is not None and unavailable_end is not None:
                            if timezone.is_naive(unavailable_start):
                                unavailable_start = timezone.make_aware(
                                    unavailable_start,
                                    timezone.get_current_timezone(),
                                )
                            if timezone.is_naive(unavailable_end):
                                unavailable_end = timezone.make_aware(
                                    unavailable_end,
                                    timezone.get_current_timezone(),
                                )
                            if _overlaps(
                                cursor,
                                slot_end,
                                unavailable_start,
                                unavailable_end,
                            ):
                                unavailable = True
                                break

                    already_reserved = any(
                        str(item["chamber_id"]) == str(chamber_obj.id)
                        and _overlaps(
                            cursor,
                            slot_end,
                            item["start_at"],
                            item["end_at"],
                        )
                        for item in reserved
                    )

                    if (
                        cursor.astimezone(datetime_timezone.utc) > timezone.now()
                        and not break_overlaps
                        and not unavailable
                        and not already_reserved
                    ):
                        slots.append(
                            {
                                "chamber": str(chamber_obj.id),
                                "start_at": cursor.astimezone(datetime_timezone.utc),
                                "end_at": slot_end.astimezone(datetime_timezone.utc),
                                "duration_minutes": duration,
                            }
                        )
                    cursor += duration_delta
        day += timedelta(days=1)

    slots.sort(key=lambda slot: (slot["start_at"], slot["chamber"]))
    return slots
