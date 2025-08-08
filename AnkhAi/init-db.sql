-- Create databases for each service
CREATE DATABASE ankhai_auth;
CREATE DATABASE ankhai_outfits;
CREATE DATABASE ankhai_celebrity;

-- Connect to auth database
\c ankhai_auth;

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create refresh tokens table
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Connect to outfits database
\c ankhai_outfits;

-- Create outfits table
CREATE TABLE outfits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    image_url VARCHAR(500),
    analysis_result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create clothing_items table
CREATE TABLE clothing_items (
    id SERIAL PRIMARY KEY,
    outfit_id INTEGER REFERENCES outfits(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'top', 'bottom', 'shoes', 'accessory'
    confidence_score DECIMAL(3,2),
    bounding_box JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Connect to celebrity database
\c ankhai_celebrity;

-- Create celebrities table
CREATE TABLE celebrities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    style_tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create celebrity_outfits table
CREATE TABLE celebrity_outfits (
    id SERIAL PRIMARY KEY,
    celebrity_id INTEGER REFERENCES celebrities(id) ON DELETE CASCADE,
    image_url VARCHAR(500),
    style_description TEXT,
    occasion VARCHAR(100),
    season VARCHAR(50),
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample celebrity data
INSERT INTO celebrities (name, description, style_tags) VALUES
('Zendaya', 'Known for her bold and eclectic fashion choices', ARRAY['bold', 'eclectic', 'streetwear', 'red carpet']),
('Harry Styles', 'Gender-fluid fashion icon with vintage influences', ARRAY['gender-fluid', 'vintage', 'colorful', 'experimental']),
('Beyoncé', 'Queen of glamour and sophisticated style', ARRAY['glamorous', 'sophisticated', 'powerful', 'elegant']),
('Timothée Chalamet', 'Minimalist and artistic fashion sense', ARRAY['minimalist', 'artistic', 'sophisticated', 'trendy']);

-- Create indexes for better performance
\c ankhai_auth;
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

\c ankhai_outfits;
CREATE INDEX idx_outfits_user_id ON outfits(user_id);
CREATE INDEX idx_clothing_items_outfit_id ON clothing_items(outfit_id);

\c ankhai_celebrity;
CREATE INDEX idx_celebrity_outfits_celebrity_id ON celebrity_outfits(celebrity_id);
