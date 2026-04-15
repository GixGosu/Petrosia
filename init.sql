-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Articles table
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft'
);

-- Article content per language
CREATE TABLE IF NOT EXISTS article_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    embedding vector(384),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(255),
    UNIQUE(article_id, language)
);

-- Version history
CREATE TABLE IF NOT EXISTS article_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_content_id UUID REFERENCES article_content(id),
    title VARCHAR(500),
    body TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    provider VARCHAR(50),
    sources JSONB,
    session_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_article_content_language ON article_content(language);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);

-- TRACK 2: api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    permissions JSONB DEFAULT '["read"]',
    namespace VARCHAR(100) DEFAULT 'default',
    is_active BOOLEAN DEFAULT true
);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_namespace ON api_keys(namespace);

-- TRACK 3: model column on chat_history
ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS model VARCHAR(100);

-- TRACK 5: namespace on articles
ALTER TABLE articles ADD COLUMN IF NOT EXISTS namespace VARCHAR(100) DEFAULT 'default' NOT NULL;
CREATE INDEX IF NOT EXISTS idx_articles_namespace ON articles(namespace);

-- Composite unique constraint: same slug allowed in different namespaces
-- Only drop old constraint if the new one doesn't exist yet (atomic swap)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_article_slug_namespace'
    ) THEN
        -- Drop old single-column unique on slug if it exists
        IF EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'articles_slug_key'
        ) THEN
            ALTER TABLE articles DROP CONSTRAINT articles_slug_key;
        END IF;
        ALTER TABLE articles ADD CONSTRAINT uq_article_slug_namespace UNIQUE (slug, namespace);
    END IF;
END $$;
