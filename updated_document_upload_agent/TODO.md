# TODO

- [x] Locate all frontend fields for `username` in view/update flows.
- [x] Add `phone_number` input field to both View and Update sections.
- [x] Update frontend JS to allow lookup by either `name` OR `mobile/phone` (AND/OR logic).
- [x] Backend: update `/api/get_person_docs` to accept `phone_number` and search persons by `mobile_number` (unique key).
- [x] Backend: update `/api/update_document` to accept `phone_number` optionally, and use it for person lookup if provided; otherwise continue extracting from Aadhaar.
- [x] Backend: update Supabase helper functions if needed to support lookup by mobile_number.
- [x] Testing: run basic local checks for view/update requests payloads.


