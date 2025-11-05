-- Main help requests table
CREATE TABLE IF NOT EXISTS help_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Caller info
    caller_id TEXT NOT NULL,
    caller_phone TEXT,
    
    -- Request details
    question TEXT NOT NULL,
    escalation_reason TEXT,
    call_transcript TEXT,
    
    -- Lifecycle tracking
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT DEFAULT 'normal',
    
    -- Resolution
    supervisor_response TEXT,
    supervisor_id TEXT,
    resolved_at TIMESTAMP,
    
    -- Follow-up tracking
    followed_up BOOLEAN DEFAULT 0,
    follow_up_attempts INTEGER DEFAULT 0,
    follow_up_method TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK(status IN ('pending', 'resolved', 'unresolved', 'escalated')),
    CHECK(priority IN ('normal', 'high', 'urgent'))
);

-- Request-KB mapping table
CREATE TABLE IF NOT EXISTS request_kb_mapping (
    request_id INTEGER NOT NULL,
    kb_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (request_id, kb_id),
    FOREIGN KEY (request_id) REFERENCES help_requests(id),
    FOREIGN KEY (kb_id) REFERENCES knowledge_base(id)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_status_created 
    ON help_requests(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_caller_created
    ON help_requests(caller_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_priority_status
    ON help_requests(priority, status);
