import datetime
from collections.abc import Callable
from importlib.metadata import version as _get_version
from typing import Any

from lxml import etree


class Header:
    def __init__(
        self,
        element: etree._Element | None,
        identifier: object,
        datestamp: datetime.datetime,
        setspec: list[str],
        deleted: bool,
    ) -> None:
        self._element = element
        # force identifier to be a string, it might be
        # an lxml.etree._ElementStringResult...
        self._identifier = str(identifier)
        self._datestamp = datestamp
        self._setspec = setspec
        self._deleted = deleted

    def element(self) -> etree._Element | None:
        return self._element

    def identifier(self) -> str:
        return self._identifier

    def datestamp(self) -> datetime.datetime:
        return self._datestamp

    def setSpec(self) -> list[str]:
        return self._setspec

    def isDeleted(self) -> bool:
        return self._deleted


class Metadata:
    def __init__(self, element: etree._Element | None, map: dict[str, Any]) -> None:
        self._element = element
        self._map = map

    def element(self) -> etree._Element | None:
        return self._element

    def getMap(self) -> dict[str, Any]:
        return self._map

    def getField(self, name: str) -> Any:
        return self._map[name]

    __getitem__ = getField


class Identify:
    def __init__(
        self,
        repositoryName: str,
        baseURL: str,
        protocolVersion: str,
        adminEmails: list[str],
        earliestDatestamp: datetime.datetime,
        deletedRecord: str,
        granularity: str,
        compression: list[str],
        toolkit_description: bool = True,
    ) -> None:
        self._repositoryName = repositoryName
        self._baseURL = baseURL
        self._protocolVersion = protocolVersion
        self._adminEmails = adminEmails
        self._earliestDatestamp = earliestDatestamp
        self._deletedRecord = deletedRecord
        self._granularity = granularity
        self._compression = compression
        self._descriptions: list[str] = []

        if toolkit_description:
            try:
                version = "<version>{}</version>".format(_get_version("oaipmh"))
            except Exception:
                version = ""
            self.add_description(
                "<toolkit xsi:schemaLocation="
                '"http://oai.dlib.vt.edu/OAI/metadata/toolkit '
                'http://oai.dlib.vt.edu/OAI/metadata/toolkit.xsd" '
                'xmlns="http://oai.dlib.vt.edu/OAI/metadata/toolkit" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                "<title>oaipmh</title>"
                f"{version}"
                "<URL>https://github.com/eth-library/oaipmh</URL>"
                "</toolkit>"
            )

    def repositoryName(self) -> str:
        return self._repositoryName

    def baseURL(self) -> str:
        return self._baseURL

    def protocolVersion(self) -> str:
        return self._protocolVersion

    def adminEmails(self) -> list[str]:
        return self._adminEmails

    def earliestDatestamp(self) -> datetime.datetime:
        return self._earliestDatestamp

    def deletedRecord(self) -> str:
        return self._deletedRecord

    def granularity(self) -> str:
        return self._granularity

    def compression(self) -> list[str]:
        return self._compression

    def add_description(self, xml_string: str) -> None:
        self._descriptions.append(xml_string)

    def descriptions(self) -> list[str]:
        return self._descriptions


def ResumptionTokenSpec(dict: dict[str, str]) -> dict[str, str]:
    dict = dict.copy()
    dict["resumptionToken"] = "exclusive"
    return dict


class OAIMethodImpl:
    def __init__(self, verb: str) -> None:
        self._verb = verb

    def __call__(self, bound_self: "OAIPMH | ResumptionOAIPMH", **kw: Any) -> Any:
        return bound_self.handleVerb(self._verb, kw)


def OAIMethod(verb: str) -> Callable[..., Any]:
    obj = OAIMethodImpl(verb)

    def method(self: "OAIPMH | ResumptionOAIPMH", **kw: Any) -> Any:
        return obj(self, **kw)

    return method


class OAIPMH:
    """Mixin that implements the Python-level OAI-PMH interface.

    It does not include resumptionToken handling.

    It passes the calls on to the 'handleVerb' method, which should be
    overridden in a subclass.
    """

    def handleVerb(self, verb: str, kw: dict[str, Any]) -> Any:
        raise NotImplementedError

    getRecord: Callable[..., Any] = OAIMethod(
        "GetRecord",
    )

    getMetadata: Callable[..., Any] = OAIMethod(
        "GetMetadata",
    )

    identify: Callable[..., Any] = OAIMethod(
        "Identify",
    )

    listIdentifiers: Callable[..., Any] = OAIMethod(
        "ListIdentifiers",
    )

    listMetadataFormats: Callable[..., Any] = OAIMethod(
        "ListMetadataFormats",
    )

    listRecords: Callable[..., Any] = OAIMethod(
        "ListRecords",
    )

    listSets: Callable[..., Any] = OAIMethod(
        "ListSets",
    )


class ResumptionOAIPMH:
    """Mixin that implements the Resumption-capable OAI-PMH interface.

    It passes the arguments on to the 'handleVerb' method, which
    should be overridden in a subclass.

    The listIdentifiers, listSets and listRecords methods return
    tuples of a list and resumptionToken. If the resumptionToken
    returned is None, this indicates the end of the list is reached.
    """

    def handleVerb(self, verb: str, kw: dict[str, Any]) -> Any:
        raise NotImplementedError

    getRecord: Callable[..., Any] = OAIMethod(
        "GetRecord",
    )

    getMetadata: Callable[..., Any] = OAIMethod(
        "GetMetadata",
    )

    identify: Callable[..., Any] = OAIMethod(
        "Identify",
    )

    listIdentifiers: Callable[..., Any] = OAIMethod(
        "ListIdentifiers",
    )

    listMetadataFormats: Callable[..., Any] = OAIMethod(
        "ListMetadataFormats",
    )

    listRecords: Callable[..., Any] = OAIMethod(
        "ListRecords",
    )

    listSets: Callable[..., Any] = OAIMethod(
        "ListSets",
    )


def getMethodForVerb(server: Any, verb: str) -> Callable[..., Any]:
    method: Callable[..., Any] = getattr(server, verb[0].lower() + verb[1:])
    return method
