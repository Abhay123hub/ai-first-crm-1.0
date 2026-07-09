-- SQL Schema for AI-First CRM HCP Module

-- Create interactions table
CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    hcp_name VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(100),
    date DATE,
    time TIME,
    attendees TEXT,
    topics_discussed TEXT,
    sentiment VARCHAR(50),
    outcomes TEXT,
    follow_up_actions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create materials_shared table
CREATE TABLE IF NOT EXISTS materials_shared (
    id SERIAL PRIMARY KEY,
    interaction_id INT REFERENCES interactions(id) ON DELETE CASCADE,
    material_name VARCHAR(255) NOT NULL
);

-- Create samples_distributed table
CREATE TABLE IF NOT EXISTS samples_distributed (
    id SERIAL PRIMARY KEY,
    interaction_id INT REFERENCES interactions(id) ON DELETE CASCADE,
    sample_name VARCHAR(255) NOT NULL
);
