# Copyright 2003, 2004, 2005 Infrae
# Released under the BSD license (see LICENSE.txt)

import base64
import codecs
import time
import urllib.error
import urllib.request
import warnings
from collections.abc import Callable, Iterable, Iterator
from collections.abc import Set as AbstractSet
from typing import TYPE_CHECKING, Any, TypedDict, TypeVar
from urllib.parse import urlencode

from lxml import etree

from oaipmh import common, error, metadata, validation
from oaipmh.datestamp import datestamp_to_datetime, datetime_to_datestamp

if TYPE_CHECKING:
    from oaipmh.server import ServerBase

WAIT_DEFAULT = 120  # two minutes
WAIT_MAX = 5


class Error(Exception):
    pass


_T = TypeVar("_T")
_Record = tuple[common.Header, common.Metadata | None, None]
_Set = tuple[str, str, None]

# Functional syntax because the keys contain hyphens
_RetryPolicy = TypedDict(
    "_RetryPolicy",
    {
        "wait-default": float,
        "retry": int,
        "expected-errcodes": AbstractSet[int],
        "max-inline-sleep": float,
    },
)
_CustomRetryPolicy = TypedDict(
    "_CustomRetryPolicy",
    {
        "wait-default": float,
        "retry": int,
        "expected-errcodes": AbstractSet[int],
        "max-inline-sleep": float,
    },
    total=False,
)


class BaseClient(common.OAIPMH):
    # retry policy on error. Default is to retry request `WAIT_MAX` times
    # on HTTP 503 errors, waiting `WAIT_DEFAULT` before each retry
    default_retry_policy: _RetryPolicy = {
        # how many seconds should we wait before each retry
        "wait-default": WAIT_DEFAULT,
        # how many times should we retry
        "retry": WAIT_MAX,
        # which HTTP codes are expected
        "expected-errcodes": {503},
        # raise ServiceUnavailableError when Retry-After exceeds this cap (seconds)
        "max-inline-sleep": 300,
    }

    def __init__(
        self,
        metadata_registry: metadata.MetadataRegistry | None = None,
        custom_retry_policy: _CustomRetryPolicy | None = None,
    ) -> None:
        self._metadata_registry = metadata_registry or metadata.global_metadata_registry
        self._ignore_bad_character_hack: bool | int = 0
        self._day_granularity = False
        self.retry_policy = self.default_retry_policy.copy()
        if custom_retry_policy is not None:
            self.retry_policy.update(custom_retry_policy)
            if "expected-errcodes" in custom_retry_policy:
                typed = {429, 503} & custom_retry_policy["expected-errcodes"]
                if typed:
                    codes = ", ".join(str(c) for c in sorted(typed))
                    warnings.warn(
                        f"expected-errcodes containing {codes} is deprecated; "
                        f"catch RateLimitedError / ServiceUnavailableError instead",
                        DeprecationWarning,
                        stacklevel=2,
                    )

    def updateGranularity(self) -> None:
        """Update the granularity setting dependent on that the server says."""
        identify = self.identify()
        granularity = identify.granularity()
        if granularity == "YYYY-MM-DD":
            self._day_granularity = True
        elif granularity == "YYYY-MM-DDThh:mm:ssZ":
            self._day_granularity = False
        else:
            raise Error(f"Non-standard granularity on server: {granularity}")

    def handleVerb(self, verb: str, kw: dict[str, Any]) -> Any:
        # validate kw first
        validation.validateArguments(verb, kw)
        # encode datetimes as datestamps
        from_ = kw.get("from_")
        if from_ is not None:
            # turn it into 'from', not 'from_' before doing actual request
            kw["from"] = datetime_to_datestamp(from_, self._day_granularity)
        if "from_" in kw:
            # always remove it from the kw, no matter whether it be None or not
            del kw["from_"]

        until = kw.get("until")
        if until is not None:
            kw["until"] = datetime_to_datestamp(until, self._day_granularity)
        elif "until" in kw:
            # until is None but is explicitly in kw, remove it
            del kw["until"]

        # now call underlying implementation
        method_name = verb + "_impl"
        return getattr(self, method_name)(
            kw, self.makeRequestErrorHandling(verb=verb, **kw)
        )

    def getNamespaces(self) -> dict[str, str]:
        """Get OAI namespaces."""
        return {"oai": "http://www.openarchives.org/OAI/2.0/"}

    def getMetadataRegistry(self) -> metadata.MetadataRegistry:
        """Return the metadata registry in use.

        Do we want to allow the returning of the global registry?
        """
        return self._metadata_registry

    def ignoreBadCharacters(self, true_or_false: bool) -> None:
        """Set to ignore bad characters in UTF-8 input.
        This is a hack to get around well-formedness errors of
        input sources which *should* be in UTF-8 but for some reason
        aren't completely.
        """
        self._ignore_bad_character_hack = true_or_false

    def parse(self, xml: bytes) -> etree._Element:
        """Parse the XML to a lxml tree."""
        # XXX this is only safe for UTF-8 encoded content,
        # and we're basically hacking around non-wellformedness anyway,
        # but oh well
        if self._ignore_bad_character_hack:
            text = str(xml, "UTF-8", "replace")
            # also get rid of character code 12
            text = text.replace(chr(12), "?")
            xml = text.encode("UTF-8")
        if hasattr(xml, "encode"):
            xml = xml.encode("utf-8")
        return etree.XML(xml)

    # implementation of the various methods, delegated here by
    # handleVerb method

    def GetRecord_impl(self, args: dict[str, Any], tree: etree._Element) -> _Record:
        records, token = self.buildRecords(
            args["metadataPrefix"], self.getNamespaces(), self._metadata_registry, tree
        )
        assert token is None
        return records[0]

    def GetMetadata_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> etree._Element:
        return tree

    def Identify_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> common.Identify:
        namespaces = self.getNamespaces()
        evaluator = etree.XPathEvaluator(tree, namespaces=namespaces)
        identify_node = evaluator("/oai:OAI-PMH/oai:Identify")[0]
        identify_evaluator = etree.XPathEvaluator(identify_node, namespaces=namespaces)
        e = identify_evaluator

        repositoryName = e("string(oai:repositoryName/text())")
        baseURL = e("string(oai:baseURL/text())")
        protocolVersion = e("string(oai:protocolVersion/text())")
        adminEmails = e("oai:adminEmail/text()")
        earliestDatestamp = datestamp_to_datetime(
            e("string(oai:earliestDatestamp/text())")
        )
        deletedRecord = e("string(oai:deletedRecord/text())")
        granularity = e("string(oai:granularity/text())")
        compression = e("oai:compression/text()")
        # XXX description
        identify = common.Identify(
            repositoryName,
            baseURL,
            protocolVersion,
            adminEmails,
            earliestDatestamp,
            deletedRecord,
            granularity,
            compression,
        )
        return identify

    def ListIdentifiers_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> Iterator[common.Header]:
        namespaces = self.getNamespaces()

        def firstBatch() -> tuple[list[common.Header], str | None]:
            return self.buildIdentifiers(namespaces, tree)

        def nextBatch(token: str) -> tuple[list[common.Header], str | None]:
            tree = self.makeRequestErrorHandling(
                verb="ListIdentifiers", resumptionToken=token
            )
            return self.buildIdentifiers(namespaces, tree)

        return ResumptionListGenerator(firstBatch, nextBatch)

    def ListMetadataFormats_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> list[tuple[str, str, str]]:
        namespaces = self.getNamespaces()
        evaluator = etree.XPathEvaluator(tree, namespaces=namespaces)

        metadataFormat_nodes = evaluator(
            "/oai:OAI-PMH/oai:ListMetadataFormats/oai:metadataFormat"
        )
        metadataFormats: list[tuple[str, str, str]] = []
        for metadataFormat_node in metadataFormat_nodes:
            e = etree.XPathEvaluator(metadataFormat_node, namespaces=namespaces)
            metadataPrefix = e("string(oai:metadataPrefix/text())")
            schema = e("string(oai:schema/text())")
            metadataNamespace = e("string(oai:metadataNamespace/text())")
            metadataFormat = (metadataPrefix, schema, metadataNamespace)
            metadataFormats.append(metadataFormat)

        return metadataFormats

    def ListRecords_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> Iterator[_Record]:
        namespaces = self.getNamespaces()
        metadata_prefix = args["metadataPrefix"]
        metadata_registry = self._metadata_registry

        def firstBatch() -> tuple[list[_Record], str | None]:
            return self.buildRecords(
                metadata_prefix, namespaces, metadata_registry, tree
            )

        def nextBatch(token: str) -> tuple[list[_Record], str | None]:
            tree = self.makeRequestErrorHandling(
                verb="ListRecords", resumptionToken=token
            )
            return self.buildRecords(
                metadata_prefix, namespaces, metadata_registry, tree
            )

        return ResumptionListGenerator(firstBatch, nextBatch)

    def ListSets_impl(
        self, args: dict[str, Any], tree: etree._Element
    ) -> Iterator[_Set]:
        namespaces = self.getNamespaces()

        def firstBatch() -> tuple[list[_Set], str | None]:
            return self.buildSets(namespaces, tree)

        def nextBatch(token: str) -> tuple[list[_Set], str | None]:
            tree = self.makeRequestErrorHandling(verb="ListSets", resumptionToken=token)
            return self.buildSets(namespaces, tree)

        return ResumptionListGenerator(firstBatch, nextBatch)

    # various helper methods

    def buildRecords(
        self,
        metadata_prefix: str,
        namespaces: dict[str, str],
        metadata_registry: metadata.MetadataRegistry,
        tree: etree._Element,
    ) -> tuple[list[_Record], str | None]:
        # first find resumption token if available
        evaluator = etree.XPathEvaluator(tree, namespaces=namespaces)
        token = evaluator("string(/oai:OAI-PMH/*/oai:resumptionToken/text())")
        if token.strip() == "":
            token = None
        record_nodes = evaluator("/oai:OAI-PMH/*/oai:record")
        result: list[_Record] = []
        for record_node in record_nodes:
            record_evaluator = etree.XPathEvaluator(record_node, namespaces=namespaces)
            e = record_evaluator
            # find header node
            header_node = e("oai:header")[0]
            # create header
            header = buildHeader(header_node, namespaces)
            # find metadata node
            metadata_list = e("oai:metadata")
            metadata: common.Metadata | None
            if metadata_list:
                metadata_node = metadata_list[0]
                # create metadata
                metadata = metadata_registry.readMetadata(
                    metadata_prefix, metadata_node
                )
            else:
                metadata = None
            # XXX TODO: about, should be third element of tuple
            result.append((header, metadata, None))
        return result, token

    def buildIdentifiers(
        self, namespaces: dict[str, str], tree: etree._Element
    ) -> tuple[list[common.Header], str | None]:
        evaluator = etree.XPathEvaluator(tree, namespaces=namespaces)
        # first find resumption token is available
        token = evaluator("string(/oai:OAI-PMH/*/oai:resumptionToken/text())")
        #'string(/oai:OAI-PMH/oai:ListIdentifiers/oai:resumptionToken/text())')
        if token.strip() == "":
            token = None
        header_nodes = evaluator("/oai:OAI-PMH/oai:ListIdentifiers/oai:header")
        result: list[common.Header] = []
        for header_node in header_nodes:
            header = buildHeader(header_node, namespaces)
            result.append(header)
        return result, token

    def buildSets(
        self, namespaces: dict[str, str], tree: etree._Element
    ) -> tuple[list[_Set], str | None]:
        evaluator = etree.XPathEvaluator(tree, namespaces=namespaces)
        # first find resumption token if available
        token = evaluator(
            "string(/oai:OAI-PMH/oai:ListSets/oai:resumptionToken/text())"
        )
        if token.strip() == "":
            token = None
        set_nodes = evaluator("/oai:OAI-PMH/oai:ListSets/oai:set")
        sets: list[_Set] = []
        for set_node in set_nodes:
            e = etree.XPathEvaluator(set_node, namespaces=namespaces)
            # make sure we get back unicode strings instead
            # of lxml.etree._ElementUnicodeResult objects.
            setSpec = str(e("string(oai:setSpec/text())"))
            setName = str(e("string(oai:setName/text())"))
            # XXX setDescription nodes
            sets.append((setSpec, setName, None))
        return sets, token

    def makeRequestErrorHandling(self, **kw: str) -> etree._Element:
        xml = self.makeRequest(**kw)
        try:
            tree = self.parse(xml)
        except SyntaxError as err:
            raise error.XMLSyntaxError(kw) from err
        # check whether there are errors first
        e_errors = tree.xpath("/oai:OAI-PMH/oai:error", namespaces=self.getNamespaces())
        if e_errors:
            # XXX right now only raise first error found, does not
            # collect error info
            for e_error in e_errors:
                code = e_error.get("code")
                msg = e_error.text
                if code not in [
                    "badArgument",
                    "badResumptionToken",
                    "badVerb",
                    "cannotDisseminateFormat",
                    "idDoesNotExist",
                    "noRecordsMatch",
                    "noMetadataFormats",
                    "noSetHierarchy",
                ]:
                    raise error.UnknownError(
                        f"Unknown error code from server: {code}, message: {msg}"
                    )
                # find exception in error module and raise with msg
                raise getattr(error, code[0].upper() + code[1:] + "Error")(msg)
        return tree

    def makeRequest(self, **kw: str) -> bytes:
        raise NotImplementedError


class Client(BaseClient):
    def __init__(
        self,
        base_url: str,
        metadata_registry: metadata.MetadataRegistry | None = None,
        credentials: tuple[str, str] | None = None,
        local_file: bool = False,
        force_http_get: bool = False,
        custom_retry_policy: _CustomRetryPolicy | None = None,
    ) -> None:
        BaseClient.__init__(
            self, metadata_registry, custom_retry_policy=custom_retry_policy
        )
        self._base_url = base_url
        self._local_file = local_file
        self._force_http_get = force_http_get
        self._credentials: str | None
        if credentials is not None:
            credential_bytes = "{}:{}".format(*credentials).encode("utf-8")
            self._credentials = base64.b64encode(credential_bytes).decode("ascii")
        else:
            self._credentials = None

    def makeRequest(self, **kw: str) -> bytes:
        """Either load a local XML file or actually retrieve XML from a server."""
        if self._local_file:
            with codecs.open(self._base_url, "r", "utf-8") as xmlfile:
                text = xmlfile.read()
            return text.encode("ascii", "replace")
        else:
            # XXX include From header?
            headers = {"User-Agent": "pyoai"}
            if self._force_http_get:
                request_url = f"{self._base_url}?{urlencode(kw)}"
                request = urllib.request.Request(request_url, headers=headers)
            else:
                binary_data = urlencode(kw).encode("utf-8")
                request = urllib.request.Request(
                    self._base_url, data=binary_data, headers=headers
                )
            # Avoid forwarding credentials when urllib follows redirects
            if self._credentials is not None:
                request.add_unredirected_header(
                    "Authorization", "Basic " + self._credentials
                )

            return retrieveFromUrlWaiting(
                request,
                wait_max=self.retry_policy["retry"],
                wait_default=self.retry_policy["wait-default"],
                expected_errcodes=self.retry_policy["expected-errcodes"],
                max_inline_sleep=self.retry_policy["max-inline-sleep"],
            )


def buildHeader(
    header_node: etree._Element, namespaces: dict[str, str]
) -> common.Header:
    e = etree.XPathEvaluator(header_node, namespaces=namespaces)
    identifier = e("string(oai:identifier/text())")
    datestamp = datestamp_to_datetime(str(e("string(oai:datestamp/text())")))
    setspec = [str(s) for s in e("oai:setSpec/text()")]
    deleted = e("@status = 'deleted'")
    return common.Header(header_node, identifier, datestamp, setspec, deleted)


def ResumptionListGenerator(
    firstBatch: Callable[[], tuple[Iterable[_T], str | None]],
    nextBatch: Callable[[str], tuple[Iterable[_T], str | None]],
) -> Iterator[_T]:
    result, token = firstBatch()
    while 1:
        itemFound = False
        for item in result:
            yield item
            itemFound = True
        if token is None or not itemFound:
            break
        result, token = nextBatch(token)


def retrieveFromUrlWaiting(
    request: urllib.request.Request,
    wait_max: int = WAIT_MAX,
    wait_default: float = WAIT_DEFAULT,
    expected_errcodes: AbstractSet[int] = {503},  # noqa: B006  # public API; mutating the default would be a caller bug, behaviour-preserving fix deferred
    max_inline_sleep: float = 300,
) -> bytes:
    """Get text from URL, handling retryable HTTP errors.

    HTTP 429 always raises ``RateLimitedError`` (no inline sleep).
    HTTP 503 (or other codes in *expected_errcodes*) sleeps and retries
    unless ``Retry-After`` exceeds *max_inline_sleep*, in which case
    ``ServiceUnavailableError`` is raised.
    ``urllib.error.URLError`` is caught and re-raised as ``NetworkError``.
    """
    for _i in list(range(wait_max)):
        try:
            f = urllib.request.urlopen(request)
            text: bytes = f.read()
            f.close()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise error.RateLimitedError(
                    e.url,
                    e.code,
                    e.reason,
                    e.headers,
                    e.fp,
                ) from e

            if e.code in expected_errcodes:
                retryAfter: int | None
                try:
                    # A missing header gives "", which int() rejects as it did None
                    retryAfter = int(e.headers.get("Retry-After", ""))
                except (TypeError, ValueError):
                    retryAfter = None
                if retryAfter is not None and retryAfter > max_inline_sleep:
                    raise error.ServiceUnavailableError(
                        e.url,
                        e.code,
                        e.reason,
                        e.headers,
                        e.fp,
                    ) from e
                if retryAfter is None:
                    time.sleep(wait_default)
                else:
                    time.sleep(retryAfter)
            else:
                raise
        except urllib.error.URLError as e:
            raise error.NetworkError(str(e.reason), url_error=e) from e
    else:
        raise Error(f"Waited too often (more than {wait_max} times)")
    return text


class ServerClient(BaseClient):
    def __init__(
        self,
        # Quoted because ServerBase is imported only for type checking
        server: "ServerBase",
        metadata_registry: metadata.MetadataRegistry | None = None,
    ) -> None:
        BaseClient.__init__(self, metadata_registry)
        self._server = server

    def makeRequest(self, **kw: str) -> bytes:
        return self._server.handleRequest(kw)
