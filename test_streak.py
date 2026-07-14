from datetime import date, timedelta

from app import next_streak


def test_streak():
    today = date(2026, 7, 14)

    # first ever check-in
    assert next_streak(0, None, today) == (1, True)
    # consecutive day extends the streak
    assert next_streak(3, today - timedelta(days=1), today) == (4, True)
    # missed a day resets to 1
    assert next_streak(5, today - timedelta(days=2), today) == (1, True)
    # already checked in today: idempotent, no double coins
    assert next_streak(4, today, today) == (4, False)

    print("ok")


if __name__ == "__main__":
    test_streak()
