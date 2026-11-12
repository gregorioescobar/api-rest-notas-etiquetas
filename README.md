# API REST de notas con etiquetas

Servicio REST autocontenido para crear, buscar y etiquetar notas con persistencia en SQLite. Implementado con Python estándar (`http.server`, `sqlite3`, `unittest`) sin dependencias externas.

## Requisitos
- Python 3.12+

## Ejecutar el servidor
```bash
cd projects/api-rest-notas-etiquetas
python3 -m notes_api.server --host 127.0.0.1 --port 8000 --db notes.db
```
El esquema de SQLite se crea automáticamente.

## Endpoints
- `GET /health` → estado del servicio.
- `POST /notes` → crea nota. Body JSON: `{"title":"...", "content":"...", "tags":["a","b"]}`.
- `GET /notes` → lista notas. Filtros: `?q=<texto>` (title/content) y/o `?tag=<nombre>`.
- `GET /notes/{id}` → detalle de nota.
- `PUT /notes/{id}` → actualiza nota y etiquetas. Body JSON igual a POST.
- `DELETE /notes/{id}` → elimina nota.
- `GET /tags` → lista etiquetas.

Respuestas en JSON. Códigos: 200/201 éxito, 400 payload inválido, 404 no encontrado, 405 método no permitido.

## Ejemplo rápido
```bash
curl -X POST http://127.0.0.1:8000/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"Idea","content":"Probar API","tags":["dev","api"]}'

curl "http://127.0.0.1:8000/notes?tag=dev"
```

## Pruebas
```bash
python3 -m unittest discover -s tests -p 'test*.py' -v
```
