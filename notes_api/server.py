import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional, Tuple

from . import storage


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> Tuple[Optional[dict], Optional[str]]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if length <= 0:
        return None, "empty body"
    try:
        raw = handler.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, "invalid json"
    if not isinstance(data, dict):
        return None, "json body must be an object"
    return data, None


def _validate_note_payload(data: dict, require_all: bool = True) -> Tuple[Optional[dict], Optional[str]]:
    title = data.get("title")
    content = data.get("content")
    tags = data.get("tags", [])
    if require_all:
        if not isinstance(title, str) or not title.strip():
            return None, "title is required"
        if not isinstance(content, str) or not content.strip():
            return None, "content is required"
    else:
        if title is not None and (not isinstance(title, str) or not title.strip()):
            return None, "title must be a non-empty string"
        if content is not None and (not isinstance(content, str) or not content.strip()):
            return None, "content must be a non-empty string"
    if tags is None:
        tags = []
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        return None, "tags must be a list of strings"
    normalized = {
        "title": title.strip() if isinstance(title, str) else title,
        "content": content.strip() if isinstance(content, str) else content,
        "tags": tags,
    }
    return normalized, None


class NotesHandler(BaseHTTPRequestHandler):
    db_path = "notes.db"
    server_version = "NotesAPI/1.0"

    def log_message(self, fmt, *args):  # quieter tests
        return

    def _conn(self):
        conn = storage.get_connection(self.db_path)
        storage.init_db(conn)
        return conn

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/health":
            return _json_response(self, 200, {"status": "ok"})

        if path == "/tags":
            with self._conn() as conn:
                tags = storage.list_tags(conn)
            return _json_response(self, 200, {"tags": tags})

        if path == "/notes":
            q = qs.get("q", [None])[0]
            tag = qs.get("tag", [None])[0]
            with self._conn() as conn:
                notes = storage.list_notes(conn, q=q, tag=tag)
            return _json_response(self, 200, {"notes": notes})

        m = re.fullmatch(r"/notes/(\d+)", path)
        if m:
            note_id = int(m.group(1))
            with self._conn() as conn:
                note = storage.get_note(conn, note_id)
            if not note:
                return _json_response(self, 404, {"error": "note not found"})
            return _json_response(self, 200, note)

        return _json_response(self, 404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/notes":
            return _json_response(self, 404, {"error": "not found"})
        data, err = _read_json(self)
        if err:
            return _json_response(self, 400, {"error": err})
        payload, verr = _validate_note_payload(data, require_all=True)
        if verr:
            return _json_response(self, 400, {"error": verr})
        with self._conn() as conn:
            note = storage.create_note(conn, payload["title"], payload["content"], payload["tags"])
        return _json_response(self, 201, note)

    def do_PUT(self):
        parsed = urlparse(self.path)
        m = re.fullmatch(r"/notes/(\d+)", parsed.path)
        if not m:
            return _json_response(self, 404, {"error": "not found"})
        note_id = int(m.group(1))
        data, err = _read_json(self)
        if err:
            return _json_response(self, 400, {"error": err})
        payload, verr = _validate_note_payload(data, require_all=True)
        if verr:
            return _json_response(self, 400, {"error": verr})
        with self._conn() as conn:
            note = storage.update_note(conn, note_id, payload["title"], payload["content"], payload["tags"])
        if not note:
            return _json_response(self, 404, {"error": "note not found"})
        return _json_response(self, 200, note)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        m = re.fullmatch(r"/notes/(\d+)", parsed.path)
        if not m:
            return _json_response(self, 404, {"error": "not found"})
        note_id = int(m.group(1))
        with self._conn() as conn:
            deleted = storage.delete_note(conn, note_id)
        if not deleted:
            return _json_response(self, 404, {"error": "note not found"})
        return _json_response(self, 200, {"deleted": True, "id": note_id})

    def do_PATCH(self):
        return _json_response(self, 405, {"error": "method not allowed"})


def make_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    handler = type("BoundNotesHandler", (NotesHandler,), {"db_path": db_path})
    httpd = ThreadingHTTPServer((host, port), handler)
    # ensure schema exists
    with storage.get_connection(db_path) as conn:
        storage.init_db(conn)
    return httpd


def main(argv=None):
    parser = argparse.ArgumentParser(description="API REST de notas con etiquetas")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="notes.db")
    args = parser.parse_args(argv)
    httpd = make_server(args.host, args.port, args.db)
    print(f"Serving on http://{args.host}:{args.port} (db={args.db})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
