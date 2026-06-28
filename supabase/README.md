# Supabase Configuration

Database schema, migrations, and configuration for the PAN application platform.

## Overview

Supabase provides:
- PostgreSQL database
- Real-time subscriptions
- User authentication
- File storage
- Edge functions

## Project Structure

```
supabase/
├── migrations/            # Database migrations
├── seed/                  # Seed data scripts
├── functions/             # Edge functions
├── policies/              # Row Level Security (RLS) policies
├── types/                 # TypeScript types
├── config.toml           # Supabase configuration
└── README.md             # This file
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  phone VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_verified BOOLEAN DEFAULT FALSE
);
```

### Persons Table

```sql
CREATE TABLE persons (
  id UUID PRIMARY KEY,
  auth_id UUID REFERENCES users(id),
  mobile_number VARCHAR(10) UNIQUE NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Documents Table

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  person_id UUID REFERENCES persons(id),
  auth_id UUID REFERENCES users(id),
  doc_type VARCHAR(50),
  extracted_data JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Row Level Security (RLS)

Enable RLS on all tables:

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
```

### Users Policy

```sql
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  USING (id = auth.uid());
```

### Persons Policy

```sql
CREATE POLICY "Users can view own persons"
  ON persons FOR SELECT
  USING (auth_id = auth.uid());
```

### Documents Policy

```sql
CREATE POLICY "Users can view own documents"
  ON documents FOR SELECT
  USING (auth_id = auth.uid());
```

## Setup Instructions

1. Create Supabase project
2. Copy project URL and API key
3. Configure environment variables
4. Run migrations
5. Enable RLS policies

## Configuration

### Environment Variables

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## License

Proprietary and confidential.
