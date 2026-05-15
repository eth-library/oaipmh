import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class ErrorBase(Exception):
    def oainame(self):
        name = self.__class__.__name__
        # strip off 'Error' part
        name = name[:-5]
        # lowercase error name
        name = name[0].lower() + name[1:]
        return name


class BadArgumentError(ErrorBase):
    pass


class BadVerbError(ErrorBase):
    pass


class BadResumptionTokenError(ErrorBase):
    pass


class CannotDisseminateFormatError(ErrorBase):
    pass


class IdDoesNotExistError(ErrorBase):
    pass


class NoRecordsMatchError(ErrorBase):
    pass


class NoMetadataFormatsError(ErrorBase):
    pass


class NoSetHierarchyError(ErrorBase):
    pass


class UnknownError(ErrorBase):
    pass


# errors not defined by OAI-PMH but which can occur in a client when
# the server is somehow misbehaving
class ClientError(Exception):
    def details(self):
        """Error details in human readable text."""
        raise NotImplementedError


class XMLSyntaxError(ClientError):
    """The OAI-PMH XML can not be parsed as it is not well-formed."""

    def details(self):
        return (
            "The data delivered by the server could not be parsed, as it "
            "is not well-formed XML."
        )


class DatestampError(ClientError):
    """The OAI-PMH datestamps were not proper UTC datestamps as by spec."""

    def __init__(self, datestamp):
        self.datestamp = datestamp

    def details(self):
        return f"An illegal datestamp was encountered: {self.datestamp}"


class NetworkError(ClientError):
    """A transport-level failure (DNS, connection refused, timeout)."""

    def __init__(self, message, url_error=None):
        self.url_error = url_error
        super().__init__(message)

    def details(self):
        return f"Network error: {self}"


# ---------------------------------------------------------------------------
# HTTP retry-after exceptions
#
# These inherit from urllib.error.HTTPError so existing ``except HTTPError:``
# catch sites continue to match.  Retry-After parsing follows RFC 9110
# section 10.2.3 (delta-seconds and HTTP-date).
# ---------------------------------------------------------------------------


def _parse_retry_after(headers):
    """Return (seconds: int | None, http_date: datetime | None, raw: str | None).

    *headers* is an ``http.client.HTTPMessage`` (or compatible mapping).
    """
    raw = headers.get("Retry-After") if headers is not None else None
    if raw is None:
        return None, None, None

    raw = raw.strip()

    # Try delta-seconds first (integer).
    try:
        delta = int(raw)
    except (ValueError, OverflowError):
        pass
    else:
        if delta < 0:
            return None, None, raw
        return delta, None, raw

    # Try HTTP-date (RFC 9110 section 5.6.7).
    try:
        http_date = parsedate_to_datetime(raw)
    except (ValueError, TypeError, OverflowError):
        return None, None, raw

    if http_date.tzinfo is None:
        http_date = http_date.replace(tzinfo=timezone.utc)

    delta = int((http_date - datetime.now(timezone.utc)).total_seconds())
    if delta < 0:
        delta = 0
    return delta, http_date, raw


class HTTPRetryAfterError(urllib.error.HTTPError):
    """An HTTP error carrying parsed ``Retry-After`` header data.

    Subclasses: ``RateLimitedError`` (429), ``ServiceUnavailableError`` (503).
    """

    def __init__(self, url, code, msg, hdrs, fp):
        super().__init__(url, code, msg, hdrs, fp)
        seconds, http_date, raw = _parse_retry_after(self.headers)
        self.retry_after_seconds = seconds
        self.retry_after_http_date = http_date
        self.retry_after_raw = raw


class RateLimitedError(HTTPRetryAfterError):
    """HTTP 429 Too Many Requests."""


class ServiceUnavailableError(HTTPRetryAfterError):
    """HTTP 503 Service Unavailable with Retry-After exceeding the inline-sleep cap."""
