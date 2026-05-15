import urllib.error
import urllib.request as urllib2
import warnings
from datetime import datetime, timedelta, timezone
from unittest import TestCase, mock

from oaipmh import client, error

URLOPEN_PATH = "urllib.request.urlopen"


def http_error(code, headers=None):
    return urllib2.HTTPError(
        "mock-url",
        code,
        "error",
        headers or {},
        None,
    )


def retry_after_exc(value):
    """Build an HTTPRetryAfterError with a Retry-After header."""
    hdrs = {"Retry-After": value} if value is not None else {}
    return error.HTTPRetryAfterError(
        "http://x",
        503,
        "Unavailable",
        hdrs,
        None,
    )


# ---------------------------------------------------------------------------
# Layer 1: Exception class unit tests (no HTTP mocking)
# ---------------------------------------------------------------------------


class RetryAfterParsingTestCase(TestCase):
    def test_retry_after_delta_seconds(self):
        exc = retry_after_exc("120")
        self.assertEqual(exc.retry_after_seconds, 120)
        self.assertIsNone(exc.retry_after_http_date)

    def test_retry_after_http_date(self):
        future = datetime.now(timezone.utc) + timedelta(seconds=600)
        date_str = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
        exc = retry_after_exc(date_str)
        self.assertIsNotNone(exc.retry_after_seconds)
        self.assertGreater(exc.retry_after_seconds, 0)
        self.assertIsNotNone(exc.retry_after_http_date)

    def test_retry_after_past_http_date(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        date_str = past.strftime("%a, %d %b %Y %H:%M:%S GMT")
        exc = retry_after_exc(date_str)
        self.assertEqual(exc.retry_after_seconds, 0)
        self.assertIsNotNone(exc.retry_after_http_date)

    def test_retry_after_missing(self):
        exc = retry_after_exc(None)
        self.assertIsNone(exc.retry_after_seconds)
        self.assertIsNone(exc.retry_after_http_date)
        self.assertIsNone(exc.retry_after_raw)

    def test_retry_after_invalid(self):
        exc = retry_after_exc("not-a-number")
        self.assertIsNone(exc.retry_after_seconds)
        self.assertIsNone(exc.retry_after_http_date)
        self.assertEqual(exc.retry_after_raw, "not-a-number")

    def test_retry_after_negative(self):
        exc = retry_after_exc("-5")
        self.assertIsNone(exc.retry_after_seconds)
        self.assertIsNone(exc.retry_after_http_date)
        self.assertEqual(exc.retry_after_raw, "-5")

    def test_typed_exception_preserves_urllib_attributes(self):
        hdrs = {"Retry-After": "60"}
        exc = error.RateLimitedError(
            "http://example.com",
            429,
            "Too Many Requests",
            hdrs,
            None,
        )
        self.assertEqual(exc.code, 429)
        self.assertEqual(exc.url, "http://example.com")
        self.assertEqual(exc.reason, "Too Many Requests")
        self.assertEqual(exc.headers.get("Retry-After"), "60")

    def test_rate_limited_is_http_error(self):
        exc = error.RateLimitedError(
            "http://x",
            429,
            "Too Many Requests",
            {},
            None,
        )
        self.assertIsInstance(exc, urllib.error.HTTPError)
        self.assertIsInstance(exc, error.HTTPRetryAfterError)

    def test_service_unavailable_is_http_error(self):
        exc = error.ServiceUnavailableError(
            "http://x",
            503,
            "Unavailable",
            {},
            None,
        )
        self.assertIsInstance(exc, urllib.error.HTTPError)
        self.assertIsInstance(exc, error.HTTPRetryAfterError)

    def test_network_error_is_client_error(self):
        exc = error.NetworkError("DNS failed")
        self.assertIsInstance(exc, error.ClientError)


# ---------------------------------------------------------------------------
# Layer 2: retrieveFromUrlWaiting() behaviour tests (HTTP mock)
# ---------------------------------------------------------------------------


class RetrieveRetryBehaviourTestCase(TestCase):
    def test_429_raises_rate_limited(self):
        side = http_error(429, {"Retry-After": "60"})
        with (  # noqa: SIM117
            mock.patch(URLOPEN_PATH, side_effect=side),
            mock.patch("time.sleep") as sleep,
        ):
            with self.assertRaises(error.RateLimitedError) as ctx:
                client.retrieveFromUrlWaiting(
                    urllib2.Request("http://mock.me"),
                )
            sleep.assert_not_called()
            self.assertIsInstance(
                ctx.exception.__cause__,
                urllib.error.HTTPError,
            )

    def test_429_bypasses_expected_errcodes(self):
        side = http_error(429, {"Retry-After": "60"})
        with (  # noqa: SIM117
            mock.patch(URLOPEN_PATH, side_effect=side),
            mock.patch("time.sleep") as sleep,
        ):
            with self.assertRaises(error.RateLimitedError):
                client.retrieveFromUrlWaiting(
                    urllib2.Request("http://mock.me"),
                    expected_errcodes={429, 503},
                )
            sleep.assert_not_called()

    def test_503_cap_boundary_matrix(self):
        cases = [
            ("below cap sleeps", "120", 300, True, 120),
            ("exceeds cap raises", "600", 300, False, None),
            ("at boundary sleeps", "300", 300, True, 300),
            ("custom cap raises", "120", 60, False, None),
        ]
        for label, retry_after, cap, expect_sleep, sleep_val in cases:
            with self.subTest(label):
                side = http_error(503, {"Retry-After": retry_after})
                with (
                    mock.patch(URLOPEN_PATH, side_effect=side),
                    mock.patch("time.sleep") as sleep,
                ):
                    if expect_sleep:
                        with self.assertRaises(client.Error):
                            client.retrieveFromUrlWaiting(
                                urllib2.Request("http://mock.me"),
                                wait_max=1,
                                max_inline_sleep=cap,
                            )
                        sleep.assert_called_once_with(sleep_val)
                    else:
                        with self.assertRaises(error.ServiceUnavailableError):
                            client.retrieveFromUrlWaiting(
                                urllib2.Request("http://mock.me"),
                                max_inline_sleep=cap,
                            )
                        sleep.assert_not_called()

    def test_exhausted_retries_raises(self):
        side = http_error(503, {"Retry-After": "1"})
        with (  # noqa: SIM117
            mock.patch(URLOPEN_PATH, side_effect=side),
            mock.patch("time.sleep"),
        ):
            with self.assertRaises(client.Error, msg="Waited too often"):
                client.retrieveFromUrlWaiting(
                    urllib2.Request("http://mock.me"),
                    wait_max=2,
                    max_inline_sleep=300,
                )

    def test_urlerror_raises_network_error(self):
        url_err = urllib.error.URLError("DNS lookup failed")
        with (  # noqa: SIM117
            mock.patch(URLOPEN_PATH, side_effect=url_err),
            mock.patch("time.sleep") as sleep,
        ):
            with self.assertRaises(error.NetworkError) as ctx:
                client.retrieveFromUrlWaiting(
                    urllib2.Request("http://mock.me"),
                )
            sleep.assert_not_called()
            self.assertIs(ctx.exception.__cause__, url_err)

    def test_urlerror_mid_retry(self):
        url_err = urllib.error.URLError("connection reset")
        effects = [
            http_error(503, {"Retry-After": "1"}),
            url_err,
        ]
        with (  # noqa: SIM117
            mock.patch(URLOPEN_PATH, side_effect=effects),
            mock.patch("time.sleep"),
        ):
            with self.assertRaises(error.NetworkError) as ctx:
                client.retrieveFromUrlWaiting(
                    urllib2.Request("http://mock.me"),
                    wait_max=5,
                )
            self.assertIs(ctx.exception.__cause__, url_err)


# ---------------------------------------------------------------------------
# Layer 3: Client-level tests (deprecation + construction)
# ---------------------------------------------------------------------------


class DeprecationWarningTestCase(TestCase):
    def test_deprecation_429_in_expected(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.Client(
                "http://mock.me",
                custom_retry_policy={
                    "expected-errcodes": {429},
                },
            )
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertEqual(len(dep), 1)
        self.assertIn("429", str(dep[0].message))

    def test_deprecation_503_in_expected(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.Client(
                "http://mock.me",
                custom_retry_policy={
                    "expected-errcodes": {503},
                },
            )
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertEqual(len(dep), 1)
        self.assertIn("503", str(dep[0].message))

    def test_no_deprecation_default(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.Client("http://mock.me")
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertEqual(len(dep), 0)

    def test_no_deprecation_non_typed(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.Client(
                "http://mock.me",
                custom_retry_policy={
                    "expected-errcodes": {500},
                },
            )
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        self.assertEqual(len(dep), 0)
