# supa.py - Supabase Database Integration

## Purpose
Handles all database operations with Supabase including user management, person records, and document storage. Provides abstraction layer for database interactions.

## Key Functions

### get_or_create_person(auth_id, mobile_number, name)
Gets existing person or creates new one.
- **Uses**: mobile_number as unique key
- **Returns**: person_id (UUID)
- **Creates**: New person record if doesn't exist
- **Error Handling**: Handles foreign key constraints

### save_document(doc_type, extracted_data, auth_id, person_id)
Saves extracted document data to database.
- **Stores**: All extracted fields in JSON format
- **Links**: To user (auth_id) and person (person_id)
- **Returns**: doc_id
- **Features**: Automatic timestamp management

### get_documents_by_auth(auth_id)
Retrieves all documents for authenticated user.
- **Input**: User auth_id
- **Returns**: List of documents with metadata
- **Uses**: Query filtering by auth_id

### get_documents_by_name_or_phone(auth_id, person_name, phone_number)
Flexible retrieval by name or phone.
- **Lookup**: By person name or phone number
- **Returns**: All documents for matching person
- **Filter**: Only documents for authenticated user

### delete_old_documents(person_id)
Removes existing documents before saving new ones.
- **Purpose**: Avoid duplicate documents
- **Target**: All documents for specific person_id
- **Note**: Called before saving updated documents

## Database Schema

### users table
- id (UUID) - Primary key
- email (VARCHAR) - User email
- created_at (TIMESTAMP)

### persons table
- id (UUID) - Primary key
- auth_id (UUID) - Reference to users
- mobile_number (VARCHAR) - Unique identifier
- name (VARCHAR) - Person's name
- created_at, updated_at (TIMESTAMP)

### documents table
- id (UUID) - Primary key
- person_id (UUID) - Reference to persons
- auth_id (UUID) - Reference to users
- doc_type (VARCHAR) - Document type (aadhaar, etc.)
- extracted_data (JSONB) - All extracted fields
- created_at, updated_at (TIMESTAMP)

## Connection Management
- Uses Supabase Python client
- Credentials from environment: SUPABASE_URL, SUPABASE_KEY
- Implements connection pooling
- Error handling for connection failures

## Data Handling
- Stores complete extracted JSON in JSONB field
- Supports all field types (strings, numbers, booleans, null)
- Efficient querying on JSON fields
- Versioning through created_at/updated_at timestamps

## Security Features
- Row-level security (RLS) at database level
- Auth_id used for access control
- Users can only access their own data
- Foreign key constraints ensure data integrity

## Error Handling
- Handles foreign key constraint violations
- Provides meaningful error messages
- Implements retry logic for transient failures
- Logs database errors for debugging

## Integration Points
- Called from `app.py` endpoints
- Used by document retrieval workflows
- Part of save and update operations

## Key Features
- Mobile number as unique identifier for persons
- Support for multiple documents per person
- Complete JSON storage of extracted data
- Audit trail via timestamps
- User isolation through auth_id

## Notes
- mobile_number is critical unique key
- Documents replace on update (old versions deleted)
- JSONB field allows flexible extraction schemas
- RLS policies enforce user-level access control
