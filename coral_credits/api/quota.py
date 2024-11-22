from calendar import monthrange
from datetime import date, timedelta
from enum import Enum


class QuotaPeriod(str, Enum):
    WEEK = "week"
    MONTH = "month"

    def get_bounds_and_days(
        self, reference_date: date = None
    ) -> tuple[date, date, int]:
        """Get the start date, end date and number of days for the calendar period.

        Args:
            reference_date: The date to get the period for. Defaults to today.

        Returns:
            tuple[date, date, int]: (start_date, end_date, number_of_days)
        """
        reference_date = reference_date or date.today()

        if self == QuotaPeriod.WEEK:
            # Get Monday (0) through Sunday (6)
            start_date = reference_date - timedelta(days=reference_date.weekday())
            end_date = start_date + timedelta(days=6)
            days = 7
        elif self == QuotaPeriod.MONTH:
            start_date = reference_date.replace(day=1)
            _, last_day = monthrange(reference_date.year, reference_date.month)
            end_date = reference_date.replace(day=last_day)
            days = last_day

        return start_date, end_date, days

    @classmethod
    def from_string(cls, period: str) -> "QuotaPeriod":
        try:
            return cls(period.lower())
        except ValueError:
            raise ValueError(f"Invalid period '{period}'. Must be 'week' or 'month'")
