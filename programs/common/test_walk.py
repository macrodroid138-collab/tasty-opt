"""The concessions are measured from the median at that attempt."""

from programs.common.walk import OrderWalk


def test_credit_walk_uses_the_new_median() -> None:
    walk = OrderWalk(urgent=False)
    walk.start(1.00)
    # tries 2 and 3: median improved, so the working price stays 1.00
    walk.unfilled(1.04)
    walk.unfilled(1.03)
    # try 4 is the new median minus two cents
    status = walk.unfilled(0.96)
    assert status.attempt == 4
    assert abs(status.working - 0.94) < 1e-9
    walk.unfilled(0.96)
    status = walk.unfilled(0.97)
    # the fifth is not stacked; the sixth replaces the two cents with five
    assert status.attempt == 6
    assert abs(status.working - 0.92) < 1e-9


def test_abort_when_the_median_runs_away() -> None:
    walk = OrderWalk(urgent=False)
    walk.start(1.00)
    status = walk.unfilled(0.94)
    assert status.phase == "aborted"


def test_urgent_pays_five_cents_on_the_second_look() -> None:
    walk = OrderWalk(urgent=True)
    walk.start(1.00, blown_through=True)
    assert abs(walk.status.working - 0.95) < 1e-9


if __name__ == "__main__":
    test_credit_walk_uses_the_new_median()
    test_abort_when_the_median_runs_away()
    test_urgent_pays_five_cents_on_the_second_look()
    print("walk checks passed")
