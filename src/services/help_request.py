import sqlite3
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
import logging
from src.core.dependencies import get_knowledge_base_service
from src.core.logging import get_plain_logger

logger = get_plain_logger(__name__)


class RequestStatus(Enum):
    """Help request lifecycle states"""
    PENDING = "pending"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ESCALATED = "escalated"


class RequestPriority(Enum):
    """Request priority levels"""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class HelpRequestService:
    """
    Manages help requests from AI to human supervisor
    """
    
    def __init__(self, db_path: str = "salon_data.db", timeout_hours: int = 24):
        self.db_path = db_path
        self.timeout_hours = timeout_hours
        self._init_db()
    
    def _init_db(self):
        """
        Initialize database schema
        
        Note: In production, would use migration tool (Alembic, Flyway)
        for versioned schema changes. Keeping inline for demo simplicity.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open("src/database/help_requests.sql", "r", encoding="utf-8") as f:
            sql = f.read()
            cursor.executescript(sql)
            logger.info("Help request tables initialized")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    
    async def create_request(
        self, 
        caller_id: str, 
        question: str,
        escalation_reason: str = "",
        caller_phone: Optional[str] = None,
        call_transcript: Optional[str] = None,
        priority: str = "normal"
    ) -> int:
        """
        Create new help request
        
        Returns:
            request_id: ID of created request
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO help_requests 
            (caller_id, caller_phone, question, escalation_reason, call_transcript, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (caller_id, caller_phone, question, escalation_reason, call_transcript, priority))
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"📝 Created help request #{request_id}: {question[:50]}... [Priority: {priority}]")
        
        # Simulate notification to supervisor
        self._notify_supervisor(request_id, question, escalation_reason, priority)
        
        return request_id
    
    def _notify_supervisor(self, request_id: int, question: str, reason: str, priority: str):
        """
        Simulate notifying supervisor (console log or webhook)
        In production: send SMS, push notification, or webhook
        """
        emoji = "🚨" if priority == "urgent" else "🔔"
        message = f"""
        {emoji} NEW HELP REQUEST #{request_id} [{priority.upper()}]
        Question: {question}
        Reason: {reason}
        Time: {datetime.now().strftime('%I:%M %p')}
        
        → View in admin panel to respond
        """
        logger.warning(message)
        
        # TODO: In production, call notification service:
        # await notification_service.send_supervisor_alert(request_id, priority)
    
    async def resolve_request(
        self, 
        request_id: int, 
        supervisor_response: str,
        supervisor_id: str = "admin",
        add_to_kb: bool = True,
        kb_category: Optional[str] = None
    ) -> dict:
        """
        Supervisor provides answer to help request
        Atomic operation with proper transaction handling
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # Get request details
            cursor.execute("""
                SELECT caller_id, caller_phone, question, status
                FROM help_requests
                WHERE id = ?
            """, (request_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Request {request_id} not found")
            
            caller_id, caller_phone, question, status = result
            
            if status != RequestStatus.PENDING.value:
                raise ValueError(f"Request {request_id} is not pending (status: {status})")
            
            logger.info(f"📱 Resolving request #{request_id}: {question[:50]}...")
            
            # Update request status
            cursor.execute("""
                UPDATE help_requests
                SET status = ?,
                    supervisor_response = ?,
                    supervisor_id = ?,
                    resolved_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                RequestStatus.RESOLVED.value, 
                supervisor_response, 
                supervisor_id,
                datetime.now(), 
                datetime.now(),
                request_id
            ))
            
            conn.commit()
            logger.info(f"✅ Resolved request #{request_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error resolving request: {e}")
            raise
        finally:
            conn.close()
        
        # Add to knowledge base (outside transaction)
        kb_id = None
        if add_to_kb:
            kb = get_knowledge_base_service()
            kb_id = await kb.add_answer(
                question, 
                supervisor_response, 
                source="supervisor",
                category=kb_category,
                created_by=supervisor_id
            )
            
            # Link request to KB entry
            if kb_id:
                await self._link_request_to_kb(request_id, kb_id)
        
        # Follow up with customer
        await self._follow_up_with_customer(
            request_id, caller_id, caller_phone, question, supervisor_response
        )
        
        return {
            "request_id": request_id,
            "caller_id": caller_id,
            "caller_phone": caller_phone,
            "question": question,
            "response": supervisor_response,
            "kb_id": kb_id
        }
    
    async def _link_request_to_kb(self, request_id: int, kb_id: int):
        """Link resolved request to its KB entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO request_kb_mapping (request_id, kb_id)
                VALUES (?, ?)
            """, (request_id, kb_id))
            conn.commit()
            logger.info(f"Linked request #{request_id} to KB entry #{kb_id}")
        except sqlite3.IntegrityError:
            # Already linked
            pass
        finally:
            conn.close()
    
    async def _follow_up_with_customer(
        self, 
        request_id: int,
        caller_id: str, 
        caller_phone: Optional[str],
        question: str, 
        answer: str
    ):
        """
        Send answer back to customer
        Simulated via console log (in production: SMS/call via Twilio)
        """
        follow_up_method = "sms" if caller_phone else "callback"
        
        message = f"""
        📱 FOLLOW-UP TO CUSTOMER (Request #{request_id})
        To: {caller_phone or caller_id}
        Method: {follow_up_method}
        
        "Hi! You asked: '{question}'
        
        Here's the answer: {answer}
        
        Feel free to call us if you have any other questions!
        
        - Glamour Salon"
        """
        logger.info(message)
        
        # Update follow-up tracking
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE help_requests
            SET followed_up = 1,
                follow_up_attempts = follow_up_attempts + 1,
                follow_up_method = ?,
                updated_at = ?
            WHERE id = ?
        """, (follow_up_method, datetime.now(), request_id))
        conn.commit()
        conn.close()
        
        # TODO: In production:
        # await notification_service.send_customer_response(caller_phone, message)
    
    def get_pending_requests(self, priority_filter: Optional[str] = None) -> List[dict]:
        """Get all pending help requests for admin UI"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if priority_filter:
            cursor.execute("""
                SELECT id, caller_id, caller_phone, question, escalation_reason, 
                       priority, created_at, call_transcript
                FROM help_requests
                WHERE status = ? AND priority = ?
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        ELSE 3 
                    END,
                    created_at DESC
            """, (RequestStatus.PENDING.value, priority_filter))
        else:
            cursor.execute("""
                SELECT id, caller_id, caller_phone, question, escalation_reason, 
                       priority, created_at, call_transcript
                FROM help_requests
                WHERE status = ?
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        ELSE 3 
                    END,
                    created_at DESC
            """, (RequestStatus.PENDING.value,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "caller_id": r[1],
                "caller_phone": r[2],
                "question": r[3],
                "escalation_reason": r[4],
                "priority": r[5],
                "created_at": r[6],
                "call_transcript": r[7],
                "age_hours": self._get_age_hours(r[6])
            }
            for r in results
        ]
    
    def get_all_requests(self, status: Optional[str] = None) -> List[dict]:
        """Get all help requests with optional status filter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT id, caller_id, question, status, supervisor_response,
                       supervisor_id, priority, created_at, resolved_at, 
                       followed_up, follow_up_attempts
                FROM help_requests
                WHERE status = ?
                ORDER BY created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT id, caller_id, question, status, supervisor_response,
                       supervisor_id, priority, created_at, resolved_at, 
                       followed_up, follow_up_attempts
                FROM help_requests
                ORDER BY created_at DESC
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "caller_id": r[1],
                "question": r[2],
                "status": r[3],
                "supervisor_response": r[4],
                "supervisor_id": r[5],
                "priority": r[6],
                "created_at": r[7],
                "resolved_at": r[8],
                "followed_up": bool(r[9]),
                "follow_up_attempts": r[10]
            }
            for r in results
        ]
    
    async def check_timeouts(self):
        """
        Check for timed-out requests and mark as unresolved
        Should be run periodically (e.g., every hour via cron/scheduler)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timeout_threshold = datetime.now() - timedelta(hours=self.timeout_hours)
        
        cursor.execute("""
            UPDATE help_requests
            SET status = ?,
                updated_at = ?
            WHERE status = ?
            AND created_at < ?
        """, (
            RequestStatus.UNRESOLVED.value, 
            datetime.now(),
            RequestStatus.PENDING.value, 
            timeout_threshold
        ))
        
        timed_out_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if timed_out_count > 0:
            logger.warning(f"⏰ Marked {timed_out_count} requests as unresolved (timeout)")
        
        return timed_out_count
    
    def _get_age_hours(self, created_at: str) -> float:
        """Calculate how many hours old a request is"""
        created = datetime.fromisoformat(created_at)
        age = datetime.now() - created
        return age.total_seconds() / 3600
    
    def get_stats(self) -> dict:
        """Get statistics for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                COUNT(CASE WHEN status = 'unresolved' THEN 1 END) as unresolved,
                COUNT(CASE WHEN priority = 'urgent' AND status = 'pending' THEN 1 END) as urgent_pending,
                COUNT(*) as total,
                AVG(CASE 
                    WHEN status = 'resolved' AND resolved_at IS NOT NULL 
                    THEN (julianday(resolved_at) - julianday(created_at)) * 24 
                END) as avg_resolution_hours
            FROM help_requests
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "pending": result[0] or 0,
            "resolved": result[1] or 0,
            "unresolved": result[2] or 0,
            "urgent_pending": result[3] or 0,
            "total": result[4] or 0,
            "avg_resolution_hours": round(result[5], 2) if result[5] else 0
        }