import json
import os
import tempfile
import threading
import unittest
from urllib import request, error

from notes_api.server import make_server


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        cls.tmp.close()
        cls.httpd = make_server("127.0.0.1", 0, cls.tmp.name)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        os.unlink(cls.tmp.name)

    def req(self, method, path, payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else None
        except error.HTTPError as e:
            body = e.read().decode("utf-8")
            return e.code, json.loads(body) if body else None

    def test_health(self):
        status, body = self.req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_crud_search_and_tags(self):
        # create
        status, note = self.req("POST", "/notes", {"title": "Nota 1", "content": "Hola mundo", "tags": ["Dev", "API"]})
        self.assertEqual(status, 201)
        nid = note["id"]
        self.assertEqual(sorted(note["tags"]), ["api", "dev"])
        # get
        status, got = self.req("GET", f"/notes/{nid}")
        self.assertEqual(status, 200)
        self.assertEqual(got["title"], "Nota 1")
        # list/search
        self.req("POST", "/notes", {"title": "Otra", "content": "Sin match", "tags": ["dev"]})
        status, body = self.req("GET", "/notes?q=mundo")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["notes"]), 1)
        status, body = self.req("GET", "/notes?tag=api")
        self.assertEqual(len(body["notes"]), 1)
        status, body = self.req("GET", "/tags")
        self.assertEqual(body["tags"], ["api", "dev"])
        # update
        status, upd = self.req("PUT", f"/notes/{nid}", {"title": "Nota 1b", "content": "Cambiado", "tags": ["nuevo"]})
        self.assertEqual(status, 200)
        self.assertEqual(upd["tags"], ["nuevo"])
        # delete
        status, body = self.req("DELETE", f"/notes/{nid}")
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])
        status, body = self.req("GET", f"/notes/{nid}")
        self.assertEqual(status, 404)

    def test_errors(self):
        status, _ = self.req("GET", "/notes/9999")
        self.assertEqual(status, 404)
        status, body = self.req("POST", "/notes", {"title": "", "content": "x", "tags": []})
        self.assertEqual(status, 400)
        status, body = self.req("PUT", "/notes/9999", {"title": "t", "content": "c", "tags": []})
        self.assertEqual(status, 404)
        status, body = self.req("DELETE", "/notes/9999")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
