# -*- coding: utf-8 -*-
"""
Test suite for Russian linguistic purity and Chimera prevention.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
from validate_russian_purity import main as validate_purity

class TestRussianPurity(unittest.TestCase):
    def test_russian_purity(self):
        self.assertTrue(validate_purity(), "Linguistic purity validation failed! Found foreign tokens or CJK in Russian text.")

if __name__ == '__main__':
    unittest.main()

