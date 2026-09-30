import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    def test_all_approved_pages_render(self):
        pages = [
            "Risk overview",
            "Transaction review",
            "Customer behaviour",
            "Group analysis",
            "Molecule & brand",
            "Financial impact",
        ]
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=90).run()
        self.assertFalse(app.exception)
        for page in pages:
            app.radio[0].set_value(page).run(timeout=90)
            self.assertFalse(app.exception, f"Page failed: {page}")


if __name__ == "__main__":
    unittest.main()
