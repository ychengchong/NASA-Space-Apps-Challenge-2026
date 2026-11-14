from app.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_within_a_minute() -> None:
    limiter = RateLimiter(3, clock=FakeClock())
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]


def test_window_slides_after_sixty_seconds() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, clock=clock)
    assert limiter.allow("a")
    clock.now = 59.9
    assert not limiter.allow("a")
    clock.now = 60.0
    assert limiter.allow("a")


def test_keys_are_counted_separately() -> None:
    limiter = RateLimiter(1, clock=FakeClock())
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")
