class IOAI:
    def getRecord(self, metadataPrefix, identifier):
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

    def identify(self):
        """Retrieve information about the repository.

        Returns an Identify object describing the repository.
        """
        raise NotImplementedError

    def listIdentifiers(self, metadataPrefix, set=None, from_=None, until=None):
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

    def listMetadataFormats(self, identifier=None):
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

    def listRecords(self, metadataPrefix, set=None, from_=None, until=None):
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

    def listSets(self):
        """Get a list of sets in the repository.

        Should raise error.NoSetHierarchyError if the repository does not
        support sets.

        Returns an iterable of setSpec, setName tuples (strings).
        """
        raise NotImplementedError


class IBatchingOAI:
    """Very similar to IOAI, but the implementation can be batch-aware.

    Methods that support resumption will get two extra arguments,
    cursor and batch_size, which indicate the batch currently being
    requested.
    """

    def getRecord(self, metadataPrefix, identifier):
        raise NotImplementedError

    def identify(self):
        raise NotImplementedError

    def listIdentifiers(
        self, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10
    ):
        raise NotImplementedError

    def listMetadataFormats(self, identifier=None):
        raise NotImplementedError

    def listRecords(
        self, metadataPrefix, set=None, from_=None, until=None, cursor=0, batch_size=10
    ):
        raise NotImplementedError

    def listSets(self):
        raise NotImplementedError


class IIdentify:
    def repositoryName(self):
        """Name of repository."""
        raise NotImplementedError

    def baseURL(self):
        """Base URL for OAI-PMH requests."""
        raise NotImplementedError

    def protocolVersion(self):
        """OAI-PMH protocol version (should always be '2.0')"""
        raise NotImplementedError

    def adminEmails(self):
        """List of email addresses of repository administrators."""
        raise NotImplementedError

    def earliestDateStamp(self):
        """The datetime (datestamp) of the earliest record in repository."""
        raise NotImplementedError

    def deletedRecord(self):
        """Way the repository handles deleted records.

        Either 'no', 'transient' or 'persistent'.
        """
        raise NotImplementedError

    def granularity(self):
        """Datetime granularity of datestamps in repository.

        Either YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ
        """
        raise NotImplementedError

    def compression(self):
        """List of types of compression schemes supported by repository.

        'identity' is the 'do-nothing' scheme.
        """
        raise NotImplementedError


class IHeader:
    def identifier(self):
        """Repository-unique identifier of this record."""
        raise NotImplementedError

    def datestamp(self):
        """Datetime of creation, last modification or deletion of the record.

        This can be used for selective harvesting.
        """
        raise NotImplementedError

    def setSpec(self):
        """A list of sets this record is a member of."""
        raise NotImplementedError

    def isDeleted(self):
        """If true, record has been deleted."""
        raise NotImplementedError
