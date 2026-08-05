import datetime

from app.core.time import utcnow


def test_utcnow_returns_naive_datetime():
    assert utcnow().tzinfo is None


def test_utcnow_is_close_to_actual_utc_time():
    reference = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    delta = abs((utcnow() - reference).total_seconds())
    assert delta < 2


def test_utcnow_is_monotonically_non_decreasing():
    first = utcnow()
    second = utcnow()
    assert second >= first
