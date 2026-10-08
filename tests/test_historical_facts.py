# -*- coding: utf-8 -*-
"""
Pytest test suite for historical and musicological factual adherence.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
from verify_historical_facts import verify_historical_facts

def test_historical_facts():
    assert verify_historical_facts() is True, "Historical/musicological fact checking failed! Inaccuracies found in canon data."

if __name__ == '__main__':
    test_historical_facts()
    print("ALL TESTS PASSED: test_historical_facts")
