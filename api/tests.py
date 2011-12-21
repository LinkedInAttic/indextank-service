import unittest
import doctest
from api import restapi

def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(restapi))
    return suite
