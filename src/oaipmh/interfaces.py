from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from oaipmh.common import Header, Identify, Metadata


class IOAI:
    def getRecord(
        self, metadataPrefix: str, identifier: str
    ) -> tuple[Header, Metadata | None, object]:
        """Get a record for a metadataPrefix and identifier.

        metadataPrefix - identifies metadata set to retrieve
        identifier - repository-unique identifier of record

        Should raise error.CannotDisseminateFormatError if
        metadataPrefix is unknown or not supported by identifier.

        Should raise error.IdDoesNotExistError if identifier is
        unknown or illegal.

        Returns a header, metadata, about tuple describing the record.
        """
        raise NotImplementedError

    def identify(self) -> Identify:
        """Retrieve information about the repository.

        Returns an Identify object describing the repository.
        """
        raise NotImplementedError

    def listIdentifiers(
        self,
        metadataPrefix: str,
        set: str | None = None,
        from_: datetime.datetime | None = None,
        until: datetime.datetime | None = None,
    ) -> Iterable[Header]:
        """Get a list of header information on records.

        metadataPrefix - identifies metadata set to retrieve
        set - set identifier; only return headers in set (optional)
        from_ - only retrieve headers from from_ date forward (optional)
        until - only retrieve headers with dates up to and including
                until date (optional)

        Should raise error.CannotDisseminateFormatError if metadataPrefix
        is not supported by the repository.

        Should raise error.NoSetHierarchyError if the repository does not
        support sets.

        Returns an iterable of headers.
        """
        raise NotImplementedError

    def listMetadataFormats(
        self, identifier: str | None = None
    ) -> Iterable[tuple[str, str, str]]:
        """List metadata formats supported by repository or record.

        identifier - identify record for which we want to know all
                     supported metadata formats. if absent, list all metadata
                     formats supported by repository. (optional)


        Should raise error.IdDoesNotExistError if record with
        identifier does not exist.

        Should raise error.NoMetadataFormatsError if no formats are
        available for the indicated record.

        Returns an iterable of metadataPrefix, schema, metadataNamespace
        tuples (each entry in the tuple is a string).
        """
        raise NotImplementedError

    def listRecords(
        self,
        metadataPrefix: str,
        set: str | None = None,
        from_: datetime.datetime | None = None,
        until: datetime.datetime | None = None,
    ) -> Iterable[tuple[Header, Metadata | None, object]]:
        """Get a list of header, metadata and about information on records.

        metadataPrefix - identifies metadata set to retrieve
        set - set identifier; only return records in set (optional)
        from_ - only retrieve records from from_ date forward (optional)
        until - only retrieve records with dates up to and including
                until date (optional)

        Should raise error.CannotDisseminateFormatError if metadataPrefix
        is not supported by the repository.

        Should raise error.NoSetHierarchyError if the repository does not
        support sets.

        Returns an iterable of header, metadata, about tuples.
        """
        raise NotImplementedError

    def listSets(self) -> Iterable[tuple[str, str, object]]:
        """Get a list of sets in the repository.

        Should raise error.NoSetHierarchyError if the repository does not
        support sets.

        Returns an iterable of setSpec, setName, setDescription tuples.
        setSpec and setName are strings; setDescription is currently
        ignored by the server.
        """
        raise NotImplementedError


class IBatchingOAI:
    """Very similar to IOAI, but the implementation can be batch-aware.

    Methods that support resumption will get two extra arguments,
    cursor and batch_size, which indicate the batch currently being
    requested.
    """

    def getRecord(
        self, metadataPrefix: str, identifier: str
    ) -> tuple[Header, Metadata | None, object]:
        raise NotImplementedError

    def identify(self) -> Identify:
        raise NotImplementedError

    def listIdentifiers(
        self,
        metadataPrefix: str,
        set: str | None = None,
        from_: datetime.datetime | None = None,
        until: datetime.datetime | None = None,
        cursor: int = 0,
        batch_size: int = 10,
    ) -> Iterable[Header]:
        raise NotImplementedError

    def listMetadataFormats(
        self, identifier: str | None = None
    ) -> Iterable[tuple[str, str, str]]:
        raise NotImplementedError

    def listRecords(
        self,
        metadataPrefix: str,
        set: str | None = None,
        from_: datetime.datetime | None = None,
        until: datetime.datetime | None = None,
        cursor: int = 0,
        batch_size: int = 10,
    ) -> Iterable[tuple[Header, Metadata | None, object]]:
        raise NotImplementedError

    def listSets(self) -> Iterable[tuple[str, str, object]]:
        raise NotImplementedError


class IIdentify:
    def repositoryName(self) -> str:
        """Name of repository."""
        raise NotImplementedError

    def baseURL(self) -> str:
        """Base URL for OAI-PMH requests."""
        raise NotImplementedError

    def protocolVersion(self) -> str:
        """OAI-PMH protocol version (should always be '2.0')"""
        raise NotImplementedError

    def adminEmails(self) -> list[str]:
        """List of email addresses of repository administrators."""
        raise NotImplementedError

    def earliestDateStamp(self) -> datetime.datetime:
        """The datetime (datestamp) of the earliest record in repository."""
        raise NotImplementedError

    def deletedRecord(self) -> str:
        """Way the repository handles deleted records.

        Either 'no', 'transient' or 'persistent'.
        """
        raise NotImplementedError

    def granularity(self) -> str:
        """Datetime granularity of datestamps in repository.

        Either YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ
        """
        raise NotImplementedError

    def compression(self) -> list[str]:
        """List of types of compression schemes supported by repository.

        'identity' is the 'do-nothing' scheme.
        """
        raise NotImplementedError


class IHeader:
    def identifier(self) -> str:
        """Repository-unique identifier of this record."""
        raise NotImplementedError

    def datestamp(self) -> datetime.datetime:
        """Datetime of creation, last modification or deletion of the record.

        This can be used for selective harvesting.
        """
        raise NotImplementedError

    def setSpec(self) -> list[str]:
        """A list of sets this record is a member of."""
        raise NotImplementedError

    def isDeleted(self) -> bool:
        """If true, record has been deleted."""
        raise NotImplementedError
