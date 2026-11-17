import inspect
from unittest import TestCase

from oaipmh.interfaces import IOAI, IBatchingOAI, IHeader, IIdentify


def call_with_placeholders(obj, name):
    # One placeholder per required parameter; optional ones keep their defaults
    method = getattr(obj, name)
    parameters = inspect.signature(method).parameters.values()
    return method(*["placeholder" for p in parameters if p.default is p.empty])


class InterfaceTestCase(TestCase):
    def test_unimplemented_methods_raise(self):
        for cls in (IOAI, IBatchingOAI, IIdentify, IHeader):
            for name, value in vars(cls).items():
                if name.startswith("_") or not inspect.isfunction(value):
                    continue
                with (
                    self.subTest(method=f"{cls.__name__}.{name}"),
                    self.assertRaises(NotImplementedError),
                ):
                    call_with_placeholders(cls(), name)

    def test_subclass_override(self):
        class Header(IHeader):
            def identifier(self):
                return "oai:example:1"

        header = Header()
        self.assertEqual("oai:example:1", header.identifier())
        with self.assertRaises(NotImplementedError):
            header.datestamp()
