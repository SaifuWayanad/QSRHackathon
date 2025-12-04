-- Create chat_sessions table to store customer chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(255) PRIMARY KEY,
    session_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'Unique session code like SESS-001',
    customer_id VARCHAR(255) COMMENT 'Link to customer if identified',
    customer_phone VARCHAR(20) COMMENT 'Phone number for quick lookup',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active' COMMENT 'active, completed, abandoned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_session_code (session_code),
    INDEX idx_customer_id (customer_id),
    INDEX idx_customer_phone (customer_phone),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create chat_messages table to store all messages in a session
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sender VARCHAR(50) NOT NULL COMMENT 'customer or agent',
    message TEXT NOT NULL,
    metadata JSON COMMENT 'Additional data like tool calls, context, etc.',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_session_id (session_id),
    INDEX idx_sender (sender),
    INDEX idx_created_at (created_at),
    
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample query to view a session with all messages
/*
SELECT 
    cs.session_code,
    cs.customer_phone,
    c.name as customer_name,
    cm.sender,
    cm.message,
    cm.created_at
FROM chat_sessions cs
LEFT JOIN customers c ON cs.customer_id = c.id
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
WHERE cs.id = 'session-id-here'
ORDER BY cm.created_at ASC;
*/
