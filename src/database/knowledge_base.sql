CREATE TABLE IF NOT EXISTS knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Content
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    
    -- Metadata
    source TEXT DEFAULT 'supervisor',
    category TEXT,
    confidence_score REAL DEFAULT 1.0,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Quality tracking
    positive_feedback INTEGER DEFAULT 0,
    negative_feedback INTEGER DEFAULT 0,
    
    -- Lifecycle
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    
    -- Future: embeddings for semantic search
    -- In PostgreSQL: embedding_vector vector(1536)
    
    UNIQUE(question COLLATE NOCASE)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_question 
    ON knowledge_base(question COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_category_active
    ON knowledge_base(category, is_active);

-- SQLite doesn’t support partial indexes with WHERE in older versions;
-- this works fine on 3.8.0+ though:
CREATE INDEX IF NOT EXISTS idx_usage_active
    ON knowledge_base(usage_count DESC, is_active)
    WHERE is_active = 1;
