import unittest
import os
import sys
import tempfile
import sqlite3

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Trading_Backend.mt5_bridge import financial_db

class TestExecutorIdempotency(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = os.path.join(self.temp_dir.name, "test_spidy.db")
        self.original_db = getattr(financial_db, 'DB_FILE', None)
        financial_db.DB_FILE = self.db_file
        financial_db.init_db()

    def tearDown(self):
        if self.original_db:
            financial_db.DB_FILE = self.original_db
        self.temp_dir.cleanup()


    def test_financial_db_idempotency(self):
        signal_id = "test_sig_12345"
        symbol = "EURUSD"
        direction = "BUY"
        
        # 1. Record signal
        inserted = financial_db.record_signal(signal_id, symbol, direction)
        self.assertTrue(inserted)
        
        # 2. Duplicate record attempt should return False
        inserted_again = financial_db.record_signal(signal_id, symbol, direction)
        self.assertFalse(inserted_again)
        
        # 3. Check status (initially PENDING)
        self.assertFalse(financial_db.is_signal_processed(signal_id))
        
        # 4. Update status to SENT
        financial_db.update_signal_status(signal_id, "SENT", ticket=999888)
        self.assertTrue(financial_db.is_signal_processed(signal_id))

if __name__ == "__main__":
    unittest.main()

