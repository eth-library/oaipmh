import os
import urllib.request as urllib2
from datetime import datetime
from unittest import TestCase, mock

from .fakeclient import FakeClient, FakeRequestError, GranularityFakeClient

URLOPEN_PATH = "urllib.request.urlopen"

from oaipmh import client, metadata, validation  # noqa: E402, I001  # late import sequenced after URLOPEN_PATH module-level constant; out-of-order is the whole point

directory = os.path.dirname(__file__)
fake1 = os.path.join(directory, "fake1")
fakeclient = FakeClient(fake1)

fakeclient.getMetadataRegistry().registerReader("oai_dc", metadata.oai_dc_reader)


def http_error(code, headers=None):
    return urllib2.HTTPError("mock-url", code, "error", headers or {}, None)


class ClientTestCase(TestCase):
    def test_getRecord(self):
        header, metadata, about = fakeclient.getRecord(
            metadataPrefix="oai_dc", identifier="hdl:1765/315"
        )
        self.assertEqual("hdl:1765/315", header.identifier())
        self.assertEqual(["2:7"], header.setSpec())
        self.assertTrue(not header.isDeleted())

    def test_getMetadata(self):
        metadata = fakeclient.getMetadata(
            metadataPrefix="oai_dc", identifier="hdl:1765/315"
        )
        self.assertEqual(
            metadata.tag, "{http://www.openarchives.org/OAI/2.0/oai_dc/}dc"
        )

    def test_identify(self):
        identify = fakeclient.identify()
        self.assertEqual(
            "Erasmus University : Research Online", identify.repositoryName()
        )
        self.assertEqual("http://dspace.ubib.eur.nl/oai/", identify.baseURL())
        self.assertEqual("2.0", identify.protocolVersion())
        self.assertEqual(["service@ubib.eur.nl"], identify.adminEmails())
        self.assertEqual("no", identify.deletedRecord())
        self.assertEqual("YYYY-MM-DDThh:mm:ssZ", identify.granularity())
        self.assertEqual(["gzip", "compress", "deflate"], identify.compression())

    def test_listIdentifiers(self):
        headers = fakeclient.listIdentifiers(
            from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
        )
        # lazy, just test first one
        headers = list(headers)

        header = headers[0]
        self.assertEqual("hdl:1765/308", header.identifier())
        self.assertEqual(datetime(2003, 4, 15, 10, 18, 51), header.datestamp())
        self.assertEqual(["1:2"], header.setSpec())
        self.assertTrue(not header.isDeleted())
        self.assertEqual(16, len(headers))

    def test_listIdentifiers_until_none(self):
        # test listIdentifiers with until argument as None explicitly
        headers = fakeclient.listIdentifiers(
            from_=datetime(2003, 4, 10), until=None, metadataPrefix="oai_dc"
        )
        self.assertEqual(16, len(list(headers)))

    def test_listIdentifiers_from_none(self):
        # test listIdentifiers with until argument as None explicitly

        # XXX unfortunately a white box test relying on particular
        # exception behavior of the fake server. We do verify whether
        # from or from_ doesn't appear in the request args though
        try:
            headers = fakeclient.listIdentifiers(  # noqa: F841  # binding documents the call shape; test exercises the KeyError path
                from_=None,
                metadataPrefix="oai_dc",
            )
        except KeyError as e:
            self.assertEqual("metadataPrefix=oai_dc&verb=ListIdentifiers", e.args[0])

    def test_listIdentifiers_argument_error(self):
        self.assertRaises(
            validation.BadArgumentError, fakeclient.listIdentifiers, foo="bar"
        )

    def test_listRecords(self):
        records = fakeclient.listRecords(
            from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
        )
        records = list(records)
        # lazy, just test first one
        header, metadata, about = records[0]
        self.assertEqual("hdl:1765/308", header.identifier())
        self.assertEqual(datetime(2003, 4, 15, 10, 18, 51), header.datestamp())
        self.assertEqual(["1:2"], header.setSpec())
        self.assertTrue(not header.isDeleted())
        # XXX need to extend metadata tests
        self.assertEqual(
            ["Kijken in het brein: Over de mogelijkheden van neuromarketing"],
            metadata.getField("title"),
        )

    def test_listMetadataFormats(self):
        formats = fakeclient.listMetadataFormats()
        metadataPrefix, schema, metadataNamespace = formats[0]
        self.assertEqual("oai_dc", metadataPrefix)
        self.assertEqual("http://www.openarchives.org/OAI/2.0/oai_dc.xsd", schema)
        self.assertEqual(
            "http://www.openarchives.org/OAI/2.0/oai_dc/", metadataNamespace
        )

    def test_listSets(self):
        expected = [
            ("3", "Erasmus MC (University Medical Center Rotterdam)", None),
            ("3:5", "EUR Medical Dissertations", None),
        ]
        # lazy, just compare first two sets..
        sets = fakeclient.listSets()
        sets = list(sets)
        compare = [sets[0], sets[1]]
        self.assertEqual(expected, compare)

    def test_day_granularity(self):
        fakeclient = GranularityFakeClient(granularity="YYYY-MM-DDThh:mm:ssZ")
        fakeclient.updateGranularity()
        try:
            fakeclient.listRecords(
                from_=datetime(2003, 4, 10, 14, 0), metadataPrefix="oai_dc"
            )
        except FakeRequestError as e:
            self.assertEqual("2003-04-10T14:00:00Z", e.kw["from"])
        fakeclient = GranularityFakeClient(granularity="YYYY-MM-DD")
        fakeclient.updateGranularity()
        try:
            fakeclient.listRecords(
                from_=datetime(2003, 4, 10, 14, 0),
                until=datetime(2004, 6, 17, 15, 30),
                metadataPrefix="oai_dc",
            )
        except FakeRequestError as e:
            self.assertEqual("2003-04-10", e.kw["from"])
            self.assertEqual("2004-06-17", e.kw["until"])

    def test_no_retry_policy(self):
        """check request is not retried by default on HTTP 500 errors"""
        with mock.patch(URLOPEN_PATH, side_effect=http_error(500)):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(urllib2.HTTPError):
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )

    def test_custom_retry_policy(self):
        """check request is retried on 500 if asked to"""
        with mock.patch(URLOPEN_PATH, side_effect=http_error(500)):  # noqa: SIM117  # nested with-blocks read more clearly than parenthesised combined form
            with mock.patch("time.sleep") as sleep:
                urlclient = client.Client(
                    "http://mock.me",
                    custom_retry_policy={
                        "expected-errcodes": {500},
                        "wait-default": 5,
                        "retry": 3,
                    },
                )
                with self.assertRaises(client.Error):
                    urlclient.listRecords(
                        from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                    )
                self.assertEqual(sleep.call_count, 3)
                sleep.assert_has_calls([mock.call(5)] * 3)

    def test_custom_retry_policy_default_wait_max(self):
        with mock.patch(URLOPEN_PATH, side_effect=http_error(500)):  # noqa: SIM117  # nested with-blocks read more clearly than parenthesised combined form
            with mock.patch("time.sleep") as sleep:
                urlclient = client.Client(
                    "http://mock.me",
                    custom_retry_policy={
                        "expected-errcodes": {500},
                        "wait-default": 5,
                    },
                )
                with self.assertRaises(client.Error):
                    urlclient.listRecords(
                        from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                    )
                self.assertEqual(sleep.call_count, 5)
                sleep.assert_has_calls([mock.call(5)] * 5)

    def test_429_raises_rate_limited_error_with_parsed_retry_after(self):
        """HTTP 429 raises RateLimitedError; Retry-After delta-seconds parsed."""
        err = http_error(429, headers={"Retry-After": "86400"})
        with mock.patch(URLOPEN_PATH, side_effect=err):  # noqa: SIM117
            with mock.patch("time.sleep") as sleep:
                urlclient = client.Client("http://mock.me")
                with self.assertRaises(client.RateLimitedError) as ctx:
                    urlclient.listRecords(
                        from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                    )
        self.assertEqual(ctx.exception.code, 429)
        self.assertEqual(ctx.exception.retry_after_seconds, 86400)
        self.assertEqual(ctx.exception.retry_after_raw, "86400")
        # Critical: 429 must NOT trigger in-process sleep.
        sleep.assert_not_called()
        # Migration attributes preserve everything urllib's HTTPError carried.
        self.assertIs(ctx.exception.original_error, err)
        self.assertEqual(ctx.exception.url, "mock-url")
        self.assertIsNotNone(ctx.exception.headers)
        # raise ... from e preserves cause chain (PEP 3134).
        self.assertIs(ctx.exception.__cause__, err)

    def test_429_raises_even_when_in_expected_errcodes(self):
        """429 always raises RateLimitedError; expected_errcodes can't override."""
        err = http_error(429, headers={"Retry-After": "60"})
        with mock.patch(URLOPEN_PATH, side_effect=err):  # noqa: SIM117
            with mock.patch("time.sleep") as sleep:
                urlclient = client.Client(
                    "http://mock.me",
                    custom_retry_policy={"expected-errcodes": {429, 503}},
                )
                with self.assertRaises(client.RateLimitedError):
                    urlclient.listRecords(
                        from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                    )
        sleep.assert_not_called()

    def test_429_http_date_retry_after(self):
        """RFC 9110 allows HTTP-date form; parses to (positive) seconds."""
        err = http_error(429, headers={"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"})
        with mock.patch(URLOPEN_PATH, side_effect=err):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(client.RateLimitedError) as ctx:
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )
        self.assertIsNotNone(ctx.exception.retry_after_seconds)
        self.assertGreater(ctx.exception.retry_after_seconds, 0)
        self.assertEqual(ctx.exception.retry_after_raw, "Wed, 21 Oct 2099 07:28:00 GMT")

    def test_429_missing_retry_after(self):
        """Missing Retry-After header -> retry_after_seconds is None."""
        err = http_error(429, headers={})
        with mock.patch(URLOPEN_PATH, side_effect=err):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(client.RateLimitedError) as ctx:
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )
        self.assertIsNone(ctx.exception.retry_after_seconds)
        self.assertIsNone(ctx.exception.retry_after_raw)

    def test_429_invalid_retry_after(self):
        """Unparseable Retry-After -> retry_after_seconds is None, raw preserved."""
        err = http_error(429, headers={"Retry-After": "not a number"})
        with mock.patch(URLOPEN_PATH, side_effect=err):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(client.RateLimitedError) as ctx:
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )
        self.assertIsNone(ctx.exception.retry_after_seconds)
        self.assertEqual(ctx.exception.retry_after_raw, "not a number")

    def test_429_negative_retry_after_treated_as_invalid(self):
        """Negative delta-seconds is malformed per RFC 9110 -> None."""
        err = http_error(429, headers={"Retry-After": "-5"})
        with mock.patch(URLOPEN_PATH, side_effect=err):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(client.RateLimitedError) as ctx:
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )
        self.assertIsNone(ctx.exception.retry_after_seconds)

    def test_429_http_date_in_past_clamped_to_zero(self):
        """Past HTTP-date clamps to 0 (the deadline has already passed)."""
        err = http_error(429, headers={"Retry-After": "Wed, 21 Oct 2001 07:28:00 GMT"})
        with mock.patch(URLOPEN_PATH, side_effect=err):
            urlclient = client.Client("http://mock.me")
            with self.assertRaises(client.RateLimitedError) as ctx:
                urlclient.listRecords(
                    from_=datetime(2003, 4, 10), metadataPrefix="oai_dc"
                )
        self.assertEqual(ctx.exception.retry_after_seconds, 0)
