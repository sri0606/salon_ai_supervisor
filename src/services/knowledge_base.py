import sqlite3
from typing import Optional, List
from datetime import datetime
from src.core.logging import get_plain_logger

logger = get_plain_logger(__name__)


class KnowledgeBaseService:
    """
    Knowledge base for AI agent learning
    Designed for easy upgrade to vector DB later
    """
    
    def __init__(self, db_path: str = "salon_data.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """
        Initialize database schema
        
        Note: In production with PostgreSQL, would add:
        - JSONB columns for flexible metadata
        - ts_vector for full-text search
        - Vector column for embeddings (pgvector extension)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open("src/database/knowledge_base.sql", "r", encoding="utf-8") as f:
            sql = f.read()
            cursor.executescript(sql)
            logger.info("Knowledge base tables initialized")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    
    async def search(
        self, 
        query: str, 
        category: Optional[str] = None,
        threshold: float = 0.7
    ) -> Optional[dict]:
        """
        Search for relevant answer in knowledge base
        
        V1: Simple keyword matching with LIKE
        V2: PostgreSQL full-text search with ts_rank
        V3: Semantic search with cosine similarity on embeddings
        
        Args:
            query: User's question
            category: Optional category filter (hours, pricing, services)
            threshold: Similarity threshold (for future vector search)
        
        Returns:
            Dict with answer and metadata if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract keywords for simple search
        search_terms = self._extract_keywords(query)
        
        for term in search_terms:
            if category:
                cursor.execute("""
                    SELECT id, answer, question, category, confidence_score, usage_count
                    FROM knowledge_base
                    WHERE LOWER(question) LIKE LOWER(?)
                    AND category = ?
                    AND is_active = 1
                    ORDER BY usage_count DESC, confidence_score DESC
                    LIMIT 1
                """, (f"%{term}%", category))
            else:
                cursor.execute("""
                    SELECT id, answer, question, category, confidence_score, usage_count
                    FROM knowledge_base
                    WHERE LOWER(question) LIKE LOWER(?)
                    AND is_active = 1
                    ORDER BY usage_count DESC, confidence_score DESC
                    LIMIT 1
                """, (f"%{term}%",))
            
            result = cursor.fetchone()
            if result:
                kb_id, answer, matched_question, cat, confidence, usage = result
                
                # Update usage statistics
                cursor.execute("""
                    UPDATE knowledge_base
                    SET usage_count = usage_count + 1,
                        last_used_at = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.now(), datetime.now(), kb_id))
                conn.commit()
                
                logger.info(f"✓ KB hit #{kb_id}: '{matched_question}' → '{answer[:50]}...'")
                conn.close()
                
                return {
                    "id": kb_id,
                    "answer": answer,
                    "matched_question": matched_question,
                    "category": cat,
                    "confidence_score": confidence,
                    "usage_count": usage + 1
                }
        
        conn.close()
        logger.info(f"✗ No KB match for: '{query}'")
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from query
        
        V1: Simple stopword removal
        V2: Use NLP library (spaCy) for proper tokenization
        V3: Use embeddings to find semantic matches
        """
        # Remove common words
        stopwords = {
            'do', 'you', 'does', 'what', 'is', 'are', 'the', 'a', 'an', 
            'how', 'much', 'can', 'i', 'get', 'your', 'have', 'has',
            'when', 'where', 'who', 'why', 'would', 'could', 'should'
        }
        
        words = text.lower().split()
        keywords = [w.strip('?.,!') for w in words if w not in stopwords and len(w) > 2]
        
        # If no keywords, use full text
        return keywords if keywords else [text.lower()]
    
    async def add_answer(
        self, 
        question: str, 
        answer: str, 
        source: str = "supervisor",
        category: Optional[str] = None,
        created_by: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> Optional[int]:
        """
        Add new learned answer to knowledge base
        
        Args:
            question: Original customer question
            answer: Supervisor's response
            source: Where answer came from (supervisor, manual, import)
            category: Topic category (hours, pricing, services, policy)
            created_by: Who added this (supervisor ID)
            confidence_score: How confident we are (0-1)
            
        Returns:
            kb_id: ID of created/updated entry
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if similar question already exists
            cursor.execute("""
                SELECT id, answer FROM knowledge_base
                WHERE LOWER(question) = LOWER(?)
            """, (question,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing answer
                cursor.execute("""
                    UPDATE knowledge_base
                    SET answer = ?,
                        source = ?,
                        category = COALESCE(?, category),
                        confidence_score = ?,
                        updated_at = ?,
                        created_by = COALESCE(?, created_by)
                    WHERE id = ?
                """, (
                    answer, 
                    source, 
                    category,
                    confidence_score,
                    datetime.now(),
                    created_by,
                    existing[0]
                ))
                kb_id = existing[0]
                logger.info(f"📝 Updated KB entry #{kb_id}: {question}")
            else:
                # Insert new answer
                cursor.execute("""
                    INSERT INTO knowledge_base 
                    (question, answer, source, category, confidence_score, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (question, answer, source, category, confidence_score, created_by))
                kb_id = cursor.lastrowid
                logger.info(f"✨ Added new KB entry #{kb_id}: {question}")
            
            conn.commit()
            return kb_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding to KB: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_learned_answers(
        self, 
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[dict]:
        """Get all learned answers for admin UI"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT id, question, answer, source, category, confidence_score,
                       created_at, usage_count, last_used_at, positive_feedback,
                       negative_feedback, is_active, created_by
                FROM knowledge_base
                WHERE category = ?
                AND (is_active = 1 OR ? = 0)
                ORDER BY usage_count DESC, created_at DESC
            """, (category, 0 if not active_only else 1))
        else:
            cursor.execute("""
                SELECT id, question, answer, source, category, confidence_score,
                       created_at, usage_count, last_used_at, positive_feedback,
                       negative_feedback, is_active, created_by
                FROM knowledge_base
                WHERE (is_active = 1 OR ? = 0)
                ORDER BY usage_count DESC, created_at DESC
            """, (0 if not active_only else 1,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "question": r[1],
                "answer": r[2],
                "source": r[3],
                "category": r[4],
                "confidence_score": r[5],
                "created_at": r[6],
                "usage_count": r[7],
                "last_used_at": r[8],
                "positive_feedback": r[9],
                "negative_feedback": r[10],
                "is_active": bool(r[11]),
                "created_by": r[12]
            }
            for r in results
        ]
    
    def record_feedback(self, kb_id: int, is_positive: bool):
        """
        Track whether an answer was helpful
        Used to improve confidence scores over time
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        field = "positive_feedback" if is_positive else "negative_feedback"
        cursor.execute(f"""
            UPDATE knowledge_base
            SET {field} = {field} + 1,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now(), kb_id))
        
        # Optionally adjust confidence score based on feedback
        cursor.execute("""
            UPDATE knowledge_base
            SET confidence_score = CASE
                WHEN positive_feedback + negative_feedback > 0 
                THEN CAST(positive_feedback AS REAL) / (positive_feedback + negative_feedback)
                ELSE confidence_score
            END
            WHERE id = ?
        """, (kb_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded {'positive' if is_positive else 'negative'} feedback for KB #{kb_id}")
    
    def deactivate_answer(self, kb_id: int):
        """Soft delete - mark answer as inactive"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE knowledge_base
            SET is_active = 0,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now(), kb_id))
        conn.commit()
        conn.close()
        logger.info(f"Deactivated KB entry #{kb_id}")
    
    def delete_answer(self, kb_id: int):
        """Hard delete - remove answer permanently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (kb_id,))
        conn.commit()
        conn.close()
        logger.info(f"Deleted KB entry #{kb_id}")

        """Get KB statistics grouped by category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                category,
                COUNT(*) as total,
                SUM(usage_count) as total_uses,
                AVG(confidence_score) as avg_confidence
            FROM knowledge_base
            WHERE is_active = 1
            GROUP BY category
            ORDER BY total_uses DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return {
            r[0] or "uncategorized": {
                "total_entries": r[1],
                "total_uses": r[2],
                "avg_confidence": round(r[3], 2) if r[3] else 0
            }
            for r in results
        }