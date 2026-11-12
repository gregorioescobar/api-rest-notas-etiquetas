import os
import tempfile
import unittest

from notes_api import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.tmp.close()
        self.conn = storage.get_connection(self.tmp.name)
        storage.init_db(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_create_and_get_note(self):
        note = storage.create_note(self.conn, "Titulo", "Contenido", ["Trabajo", "urgente", "trabajo"])
        self.assertEqual(note["title"], "Titulo")
        self.assertEqual(note["content"], "Contenido")
        self.assertEqual(note["tags"], ["trabajo", "urgente"])  # normalized, unique, sorted in output
        fetched = storage.get_note(self.conn, note["id"])
        self.assertEqual(fetched["id"], note["id"])
        self.assertIsNone(storage.get_note(self.conn, 9999))

    def test_list_search_and_tags(self):
        n1 = storage.create_note(self.conn, "Comprar leche", "Ir al super", ["hogar"])
        n2 = storage.create_note(self.conn, "Reunion", "Hablar de leche y roadmap", ["trabajo"])
        all_notes = storage.list_notes(self.conn)
        self.assertEqual([n["id"] for n in all_notes], [n2["id"], n1["id"]])
        by_q = storage.list_notes(self.conn, q="leche")
        self.assertEqual({n["id"] for n in by_q}, {n1["id"], n2["id"]})
        by_tag = storage.list_notes(self.conn, tag="trabajo")
        self.assertEqual([n["id"] for n in by_tag], [n2["id"]])
        by_both = storage.list_notes(self.conn, q="roadmap", tag="trabajo")
        self.assertEqual([n["id"] for n in by_both], [n2["id"]])
        self.assertEqual(storage.list_tags(self.conn), ["hogar", "trabajo"])

    def test_update_and_delete(self):
        note = storage.create_note(self.conn, "A", "B", ["x"])
        updated = storage.update_note(self.conn, note["id"], "A2", "B2", ["y", "z"])
        self.assertEqual(updated["title"], "A2")
        self.assertEqual(updated["tags"], ["y", "z"])
        self.assertIsNone(storage.update_note(self.conn, 9999, "t", "c", []))
        self.assertTrue(storage.delete_note(self.conn, note["id"]))
        self.assertIsNone(storage.get_note(self.conn, note["id"]))
        self.assertFalse(storage.delete_note(self.conn, note["id"]))


if __name__ == "__main__":
    unittest.main()
