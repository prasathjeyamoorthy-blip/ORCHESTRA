# TODO

- [x] Change unique update key from `name`/username to `mobile_number`
- [x] Update `supa.py`: `get_or_create_person` to lookup persons by `(auth_id, mobile_number)`

- [x] Update `app.py`: when extracting Aadhaar, use `mobile_number` for person lookup

- [x] Update any related queries (e.g., get documents by person) if they rely on `name`

- [x] Run quick local tests by uploading Aadhaar twice with same mobile number and verify documents update


