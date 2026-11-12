# PLAN — API REST de notas con etiquetas

## Objetivo
Construir un servicio REST autocontenido para crear, buscar y etiquetar notas con persistencia en SQLite, expuesto vía HTTP y cubierto por pruebas automatizadas.

## Stack elegido (ligero y autocontenido)
- **Python 3.12+ (stdlib)**: `http.server.ThreadingHTTPServer`, `json`, `urllib.parse`, `sqlite3`, `unittest`.
- **Persistencia**: SQLite (archivo local configurable por argumento/variable, por defecto `notes.db`).
- Sin dependencias externas ni servicios adicionales.

## Tareas
1. **Scaffold y modelo de datos**
   - Estructura `notes_api/` (storage, server/app), `tests/`.
   - Tablas: `notes(id, title, content, created_at, updated_at)` y `tags(id, name)` + relación `note_tags(note_id, tag_id)` (etiquetas normalizadas, únicas).
2. **Capa de almacenamiento (SQLite)**
   - Inicialización/migración idempotente del esquema.
   - Operaciones: crear nota (con etiquetas), listar/buscar notas (por texto y/o etiqueta), obtener por id, actualizar, eliminar, listar etiquetas.
3. **API REST (HTTP/JSON)**
   - `GET /health` → estado del servicio.
   - `POST /notes` → crear nota `{title, content, tags[]}`.
   - `GET /notes` → listar; filtros `?q=<texto>` y/o `?tag=<nombre>`.
   - `GET /notes/{id}` → detalle.
   - `PUT /notes/{id}` → actualizar nota/etiquetas.
   - `DELETE /notes/{id}` → eliminar.
   - `GET /tags` → listar etiquetas.
   - Respuestas y errores JSON consistentes (400/404/405/500 según aplique).
4. **CLI/arranque del servidor**
   - `python3 -m notes_api.server --host 127.0.0.1 --port 8000 --db notes.db`.
5. **Pruebas automatizadas**
   - Unitarias/integración de storage y endpoints HTTP usando `unittest` y base temporal.
6. **Documentación**
   - `README.md` con uso, endpoints y comando de tests.

## Criterios de aceptación
- Se pueden crear notas con etiquetas y persistirlas en SQLite.
- Se pueden buscar/listar notas por texto (`q`) y por etiqueta (`tag`), y consultar detalle.
- Se pueden actualizar y eliminar notas; las etiquetas se gestionan correctamente.
- La API responde JSON con códigos HTTP adecuados (incluye 404 para inexistentes y 400 para payload inválido).
- No quedan `TODO`, `FIXME` ni stubs en el código.
- Todas las pruebas pasan con código de salida 0.

## Comando exacto para correr los tests
```bash
python3 -m unittest discover -s tests -p 'test*.py' -v
```
