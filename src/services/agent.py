from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    inference,
    function_tool,
    RunContext,
)
from livekit.plugins import silero

# Import services
from src.services.knowledge_base import KnowledgeBaseService
from src.services.help_request import HelpRequestService

from src.core.logging import get_plain_logger

logger = get_plain_logger(__name__)

load_dotenv()

# Initialize services
kb_service = KnowledgeBaseService()
help_request_service = HelpRequestService()

# Salon Business Context (System Prompt)

SALON_INSTRUCTIONS = """
## Identity

You are Jamie, a friendly and professional receptionist for Glamour Salon, a high-end hair salon.

## Business Information:

- Name: Glamour Salon
- Address: 123 Main Street, Downtown
- Phone: (555) 123-4467
- Hours: Monday-Friday 9 AM to 7 PM, Saturday 9 AM to 5 PM, Sunday Closed

## Services & Pricing:

Women's Haircut $65, Men's Haircut $45, Hair Coloring $120 to $200, Highlights $150, Blowout and Styling $55, Deep Conditioning Treatment $40

## Booking Policy:

We accept walk-ins but recommend appointments. 24-hour cancellation policy required. First-time clients get 15% off their first service.

## CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:

1. SCOPE OF KNOWLEDGE: You ONLY know the information listed above. That's it. Nothing else.

2. ANSWERING QUESTIONS:
   - If the question is about hours, services, pricing, or policies listed above: Answer directly
   - If the question is about ANYTHING else (appointments, specific stylists, product recommendations, keratin treatments, balayage, availability, specific dates, etc.): You DO NOT know the answer
   
3. WHEN YOU DON'T KNOW:
   - FIRST: Call the check_knowledge_base function with the customer's question
   - IF the knowledge base returns "No answer found": IMMEDIATELY call escalate_to_supervisor
   - DO NOT guess, make up information, or say "I can help with that" if you don't know
   - DO NOT say "let me transfer you" - just call the escalate_to_supervisor function
   
4. ESCALATION EXAMPLES - You MUST escalate for:
   - Booking appointments (you can't access the calendar)
   - Specific stylist questions
   - Specialized treatments not in your list (keratin, balayage, perms, etc.)
   - Product recommendations
   - Availability questions
   - Rescheduling or cancellations
   - Specific date/time questions
   - Gift certificates
   - Anything requiring the calendar or detailed product knowledge

5. GETTING PHONE NUMBER:
   - Before calling escalate_to_supervisor, you MUST ask: "What's the best phone number to reach you at?"
   - Wait for their response
   - Then call escalate_to_supervisor with their phone number

6. RESPONSE STYLE:
   - Keep responses short and conversational
   - No emojis, asterisks, or special formatting
   - Sound natural like you're on a phone call

7. GREETING:
   When the call starts, say: "Hello! Thank you for calling Glamour Salon. This is Jamie. How can I help you today?"


## Example Conversations

### Example 1: Direct Answer (Hours)
**Caller:** "What time are you open on Saturday?"
**You:** "We're open 9am to 7pm on Saturdays! Do you want to book an appointment?"
**Analysis:** ✓ Confident answer from business info, no escalation needed

### Example 2: Escalate (Service Not Listed)
**Caller:** "Do you do microblading?"
**You:** "Let me confirm if we offer microblading services. Can I grab your phone number? We'll text you right back with an answer and any details you need."
**Analysis:** 🚨 ESCALATE - service not in our list, verify first

### Example 3: Direct Answer (Services)
**Caller:** "Do you guys do men's haircuts?"
**You:** "Yes, we do men's haircuts! We have stylists available Tuesday through Sunday. Would you like to schedule an appointment?"
**Analysis:** ✓ Listed in services, confident answer
"""


class SalonAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SALON_INSTRUCTIONS)
        logger.info(f"🔧 Agent initialized")
    
    @function_tool
    async def check_knowledge_base(self, context: RunContext, question: str) -> str:
        """Search the knowledge base for additional information not in your basic knowledge.
        
        Use this function when a customer asks about something you don't know from your basic information.
        
        Args:
            question: The customer's exact question to search for
            
        Returns:
            Either the answer from the knowledge base, or a message telling you to escalate.
        """
        logger.info(f"🔍 Checking KB for: {question}")
        results = await kb_service.search(question)
        if results and results["confidence_score"] > 0.7:
            logger.info(f"✅ KB hit: {results}")
            return f"ANSWER FOUND: {results["answer"]}"
        else:
            logger.info("❌ KB miss")
            return "NO ANSWER FOUND. You MUST now call escalate_to_supervisor immediately. Do not make up an answer."
    
    @function_tool
    async def escalate_to_supervisor(
        self,
        context: RunContext, 
        question: str, 
        reason: str, 
        caller_phone: str
    ) -> str:
        """REQUIRED: Escalate to a human supervisor when you don't know the answer.
        
        You MUST call this function when:
        - The knowledge base returns "NO ANSWER FOUND"
        - Customer asks about appointments, bookings, or scheduling
        - Customer asks about specific stylists or availability
        - Customer asks about services not in your basic list
        - Any question you cannot answer with confidence
        
        IMPORTANT: You must get the caller's phone number BEFORE calling this function.
        If you don't have it yet, ask: "What's the best phone number to reach you at?"
        
        Args:
            question: The customer's original question that you cannot answer
            reason: Brief explanation of why you're escalating (e.g., "needs appointment booking", "asks about keratin treatment")
            caller_phone: The customer's phone number for callback (REQUIRED - must not be "unknown")
            
        Returns:
            A message confirming the escalation. Tell this to the customer.
        """
        logger.info(f"📞 Escalating: {question}")
        
        # Validate phone number
        if caller_phone == "unknown" or not caller_phone:
            return "ERROR: You must ask for the customer's phone number before escalating. Ask them: 'What's the best phone number to reach you at?'"
        
        try:
            request_id = await help_request_service.create_request(
                caller_id=caller_phone,
                caller_phone=caller_phone,
                question=question,
                escalation_reason=reason
            )
            logger.info(f"✅ Help request #{request_id} created")
            return (
                f"SUCCESS - Help request created (ID: {request_id}). "
                f"Now tell the customer: 'I've noted your question and our manager will call you back "
                f"at {caller_phone} within the hour with an answer. Is there anything else I can help you with today?'"
            )
        except Exception as e:
            logger.error(f"Error creating help request: {e}")
            return "ERROR: System issue. Tell customer: 'I apologize, I'm having a technical issue. Please call us back at 555-123-4567 and we'll help you right away.'"
    
    @function_tool
    async def get_business_hours(self, context: RunContext) -> str:
        """Return current business hours."""
        logger.info("📅 Getting business hours")
        return "Monday-Friday: 9 AM - 7 PM, Saturday: 9 AM - 5 PM, Sunday: Closed"
    
    @function_tool
    async def get_services_and_pricing(self, context: RunContext) -> str:
        """Return all services and prices."""
        logger.info("💰 Getting services and pricing")
        return """
            Women's Haircut: $65
            Men's Haircut: $45
            Hair Coloring: $120-$200
            Highlights: $150
            Blowout & Styling: $55
            Deep Conditioning Treatment: $40
            """

def prewarm(proc: JobProcess):
    """Preload models before processing jobs"""
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    """Main LiveKit agent entry point for each incoming call"""
    
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    logger.info(f"🎙️ Agent started for room: {ctx.room.name}")

    # Create agent session with voice pipeline
    session = AgentSession(
        # Speech-to-text
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        
        # Voice Activity Detection
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
    )

    # Start the session
    await session.start(
        agent=SalonAssistant(),
        room=ctx.room,
    )

    # Connect to the room
    await ctx.connect()
    
    logger.info("✅ Agent connected and ready")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm
        )
    )