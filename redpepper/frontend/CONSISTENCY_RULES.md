# Frontend-Database Consistency Rules

This project enforces a strict consistency rule:

- Database is the single source of truth.
- Any successful write operation must be followed by a full reload from backend (`_load_data`).
- Never mutate UI cache as the final state (`append`, `insert`, `pop`, direct replacement) after write APIs.

## Required Pattern

For create/update/delete/import actions:

1. Call backend write API.
2. If API succeeds, call `_load_data()` immediately.
3. Render UI from freshly loaded data only.

## Forbidden Pattern

After write API success, do not do:

- `local_list.append(created)`
- `local_list.insert(0, created)`
- `local_list[row] = updated`
- `local_list.pop(row)`

These patterns can drift from database state and create counting mismatch.

## Error Handling

- If write API fails, show error and do not modify local cache.
- If reload fails, show error and keep last rendered state.

## Review Checklist

When editing any page under `frontend/windows`:

- [ ] All write handlers (`_on_add`, `_on_edit`, `_on_delete`, import handlers) call `_load_data()` on success.
- [ ] No local cache mutation remains after write success.
- [ ] Summary labels and counters are derived from data loaded by `_load_data()`.
- [ ] Tab filters are based on canonical normalized type values.
