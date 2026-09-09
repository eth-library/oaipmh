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


def http_error(code):
    return urllib2.HTTPError("mock-url", code, "error", {}, None)


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

    @mock.patch("oaipmh.client.retrieveFromUrlWaiting", return_value=b"response")
    def test_http_basic_authentication_post(self, retrieve):
        urlclient = client.Client(
            "https://mock.me", credentials=("username", "password")
        )

        self.assertEqual(b"response", urlclient.makeRequest(verb="Identify"))

        request = retrieve.call_args.args[0]
        self.assertEqual(
            "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            request.get_header("Authorization"),
        )
        self.assertEqual(b"verb=Identify", request.data)

    @mock.patch("oaipmh.client.retrieveFromUrlWaiting", return_value=b"response")
    def test_http_basic_authentication_forced_get(self, retrieve):
        urlclient = client.Client(
            "https://mock.me",
            credentials=("username", "password"),
            force_http_get=True,
        )

        self.assertEqual(b"response", urlclient.makeRequest(verb="Identify"))

        request = retrieve.call_args.args[0]
        self.assertEqual(
            "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            request.get_header("Authorization"),
        )
        self.assertEqual("https://mock.me?verb=Identify", request.full_url)
        self.assertIsNone(request.data)

    @mock.patch("oaipmh.client.retrieveFromUrlWaiting", return_value=b"response")
    def test_request_without_credentials_omits_authorization(self, retrieve):
        urlclient = client.Client("https://mock.me")

        self.assertEqual(b"response", urlclient.makeRequest(verb="Identify"))

        request = retrieve.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))

    @mock.patch("oaipmh.client.retrieveFromUrlWaiting", return_value=b"response")
    def test_http_basic_authentication_is_not_forwarded_on_redirect(self, retrieve):
        urlclient = client.Client(
            "https://source.example/oai",
            credentials=("username", "password"),
        )
        urlclient.makeRequest(verb="Identify")

        request = retrieve.call_args.args[0]
        self.assertEqual(
            "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            request.get_header("Authorization"),
        )

        redirected_request = urllib2.HTTPRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://redirected.example/oai",
        )
        self.assertIsNone(redirected_request.get_header("Authorization"))

    @mock.patch("oaipmh.client.retrieveFromUrlWaiting", return_value=b"response")
    def test_http_basic_authentication_encodes_text_credentials(self, retrieve):
        cases = [
            (("", ""), "Basic Og=="),
            (("usér", "päss:word"), "Basic dXPDqXI6cMOkc3M6d29yZA=="),
        ]

        for credentials, expected_header in cases:
            with self.subTest(credentials=credentials):
                urlclient = client.Client(
                    "https://mock.me",
                    credentials=credentials,
                )
                urlclient.makeRequest(verb="Identify")

                request = retrieve.call_args.args[0]
                self.assertEqual(
                    expected_header,
                    request.get_header("Authorization"),
                )

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
