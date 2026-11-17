from collections.abc import Callable

from lxml import etree

from oaipmh import common

_Reader = Callable[[etree._Element], common.Metadata]
_Writer = Callable[[etree._Element, common.Metadata], None]


class MetadataRegistry:
    """A registry that contains readers and writers of metadata.

    a reader is a function that takes a chunk of (parsed) XML and
    returns a metadata object.

    a writer is a function that takes a takes a metadata object and
    produces a chunk of XML in the right format for this metadata.
    """

    def __init__(self) -> None:
        self._readers: dict[str, _Reader] = {}
        self._writers: dict[str, _Writer] = {}

    def registerReader(self, metadata_prefix: str, reader: _Reader) -> None:
        self._readers[metadata_prefix] = reader

    def registerWriter(self, metadata_prefix: str, writer: _Writer) -> None:
        self._writers[metadata_prefix] = writer

    def hasReader(self, metadata_prefix: str) -> bool:
        return metadata_prefix in self._readers

    def hasWriter(self, metadata_prefix: str) -> bool:
        return metadata_prefix in self._writers

    def readMetadata(
        self, metadata_prefix: str, element: etree._Element
    ) -> common.Metadata:
        """Turn XML into metadata object.

        element - element to read in

        returns - metadata object
        """
        return self._readers[metadata_prefix](element)

    def writeMetadata(
        self, metadata_prefix: str, element: etree._Element, metadata: common.Metadata
    ) -> None:
        """Write metadata as XML.

        element - ElementTree element to write under
        metadata - metadata object to write
        """
        self._writers[metadata_prefix](element, metadata)


global_metadata_registry: MetadataRegistry = MetadataRegistry()


class Error(Exception):
    pass


class MetadataReader:
    """A default implementation of a reader based on fields."""

    def __init__(
        self,
        fields: dict[str, tuple[str, str]],
        namespaces: dict[str, str] | None = None,
    ) -> None:
        self._fields = fields
        self._namespaces = namespaces or {}

    def __call__(self, element: etree._Element) -> common.Metadata:
        map: dict[str, str | list[str]] = {}
        # create XPathEvaluator for this element
        xpath_evaluator = etree.XPathEvaluator(element, namespaces=self._namespaces)

        e = xpath_evaluator
        # now extra field info according to xpath expr
        for field_name, (field_type, expr) in list(self._fields.items()):
            value: str | list[str]
            if field_type == "bytes":
                value = str(e(expr))
            elif field_type == "bytesList":
                value = [str(item) for item in e(expr)]
            elif field_type == "text":
                # make sure we get back unicode strings instead
                # of lxml.etree._ElementUnicodeResult objects.
                value = str(e(expr))
            elif field_type == "textList":
                # make sure we get back unicode strings instead
                # of lxml.etree._ElementUnicodeResult objects.
                value = [str(v) for v in e(expr)]
            else:
                raise Error(f"Unknown field type: {field_type}")
            map[field_name] = value
        return common.Metadata(element, map)


oai_dc_reader: MetadataReader = MetadataReader(
    fields={
        "title": ("textList", "oai_dc:dc/dc:title/text()"),
        "creator": ("textList", "oai_dc:dc/dc:creator/text()"),
        "subject": ("textList", "oai_dc:dc/dc:subject/text()"),
        "description": ("textList", "oai_dc:dc/dc:description/text()"),
        "publisher": ("textList", "oai_dc:dc/dc:publisher/text()"),
        "contributor": ("textList", "oai_dc:dc/dc:contributor/text()"),
        "date": ("textList", "oai_dc:dc/dc:date/text()"),
        "type": ("textList", "oai_dc:dc/dc:type/text()"),
        "format": ("textList", "oai_dc:dc/dc:format/text()"),
        "identifier": ("textList", "oai_dc:dc/dc:identifier/text()"),
        "source": ("textList", "oai_dc:dc/dc:source/text()"),
        "language": ("textList", "oai_dc:dc/dc:language/text()"),
        "relation": ("textList", "oai_dc:dc/dc:relation/text()"),
        "coverage": ("textList", "oai_dc:dc/dc:coverage/text()"),
        "rights": ("textList", "oai_dc:dc/dc:rights/text()"),
    },
    namespaces={
        "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
        "dc": "http://purl.org/dc/elements/1.1/",
    },
)
