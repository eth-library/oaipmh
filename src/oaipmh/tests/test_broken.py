import os
from unittest import TestCase

from oaipmh import error, metadata

from .fakeclient import FakeClient

test_directory = os.path.dirname(__file__)

class BrokenDataTestCase(TestCase):
    def createFakeClient(self, directory):
        fake = os.path.join(test_directory, directory)
        fakeclient = FakeClient(fake)
        fakeclient.getMetadataRegistry().registerReader(
            'oai_dc', metadata.oai_dc_reader)
        return fakeclient
    
    def test_notwellformed(self):
        fakeclient = self.createFakeClient('fake3')
        self.assertRaises(error.XMLSyntaxError, fakeclient.identify)

    def test_unknown_entities(self):
        fakeclient = self.createFakeClient('fake4')
        self.assertRaises(error.XMLSyntaxError, fakeclient.identify)

    def test_broken_datestamp(self):
        fakeclient = self.createFakeClient('fake5')
        self.assertRaises(error.DatestampError, fakeclient.identify)
