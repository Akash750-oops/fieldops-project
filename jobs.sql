CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    location TEXT NOT NULL,
    issue TEXT NOT NULL,
    priority TEXT CHECK (priority IN ('High', 'Medium', 'Low')),
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);