import re
from typing import Optional

# Official identity of the AI Assistant for Maharshi Dayanand University (MDU), Rohtak
MDU_GREETING_RESPONSE = (
    "Hello! I am the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak. "
    "How can I assist you with your courses, syllabi, examination datesheets, or university regulations today?"
)

MDU_IDENTITY_RESPONSE = (
    "I am the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak. "
    "I help students and faculty quickly find verified, accurate information from official university documents, "
    "including course syllabi, examination datesheets, academic council minutes, and university notifications. "
    "How can I help you today?"
)

MDU_HELP_RESPONSE = (
    "I can assist you with verified academic information from Maharshi Dayanand University (MDU), Rohtak, including:\n"
    "• Course syllabi, prerequisites, and instructor information\n"
    "• Examination datesheets, timings, and exam center guidelines\n"
    "• Academic Council and Executive Court resolutions and minutes\n"
    "• Rules regarding calculators, electronic gadgets, and examinations\n\n"
    "What would you like to know?"
)

MDU_HOW_ARE_YOU_RESPONSE = (
    "I'm doing well, thank you! I am ready to assist you with any academic questions or university information "
    "for MDU Rohtak. How can I help you today?"
)

MDU_GRATITUDE_RESPONSE = (
    "You're very welcome! If you have any more questions regarding your studies, syllabus, or university updates, "
    "feel free to ask. Best of luck with your academics at MDU Rohtak!"
)

MDU_FAREWELL_RESPONSE = (
    "Goodbye! Have a great day and best of luck with your studies at Maharshi Dayanand University (MDU), Rohtak. "
    "Feel free to reach out anytime you need assistance!"
)

# Regex patterns for pure conversational intents
RE_GREETING = re.compile(
    r"^(?:hi|hello|hey|heya|hlo|namaste|pranam|good\s+(?:morning|afternoon|evening|day)|greetings?)(?:\s+there|\s+assistant|\s+ai|\s+bot)?[\s!.,?]*$",
    re.IGNORECASE
)

RE_IDENTITY = re.compile(
    r"^(?:who\s+(?:are\s+you|are\s+u|r\s+u|developed\s+you|made\s+you|created\s+you)|"
    r"what\s+(?:are\s+you|is\s+your\s+name|is\s+this\s+ai|is\s+this\s+bot|is\s+this\s+system)|"
    r"introduce\s+(?:yourself|urself)|tell\s+me\s+about\s+(?:yourself|urself)|"
    r"which\s+(?:university\s+are\s+you\s+for|ai\s+is\s+this|university|college))[\s!.,?]*$",
    re.IGNORECASE
)

RE_HELP = re.compile(
    r"^(?:what\s+can\s+you\s+do|how\s+can\s+you\s+help(?:\s+me)?|what\s+do\s+you\s+do|help(?:\s+me)?|capabilities)[\s!.,?]*$",
    re.IGNORECASE
)

RE_HOW_ARE_YOU = re.compile(
    r"^(?:how\s+(?:are\s+you|are\s+u|r\s+u)|how\'?s\s+it\s+going|how\s+do\s+you\s+do)[\s!.,?]*$",
    re.IGNORECASE
)

RE_GRATITUDE = re.compile(
    r"^(?:thanks?|thank\s+you(?:\s+very\s+much)?|thank\s+u|thx|tysm|ok\s+thanks?|okay\s+thanks?)[\s!.,?]*$",
    re.IGNORECASE
)

RE_FAREWELL = re.compile(
    r"^(?:bye|goodbye|see\s+you|cya|see\s+ya|have\s+a\s+good\s+day)[\s!.,?]*$",
    re.IGNORECASE
)

RE_DATETIME = re.compile(
    r"^(?:what\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:date|time|day|datetime|date\s+and\s+time|today\'?s?\s+date)|"
    r"current\s+(?:date(?:\s+(?:and|&)\s+time)?|time|datetime)|"
    r"today\'?s?\s+(?:date|day)|"
    r"date\s+(?:and|&)\s+time|"
    r"what\s+day\s+is\s+it|what\s+time\s+is\s+it|what\s+is\s+today)[\s!.,?]*$",
    re.IGNORECASE
)

def get_conversational_response(question: str) -> Optional[str]:
    """
    Checks if the user's input is a pure conversational query (greeting, identity, date/time, gratitude, etc.).
    Returns a natural, friendly response as the MDU Rohtak University AI Assistant,
    or None if the query contains domain-specific academic questions requiring RAG retrieval.
    """
    if not question:
        return MDU_GREETING_RESPONSE

    cleaned = question.strip()

    # 0. Current Date / Time Inquiry
    if RE_DATETIME.match(cleaned):
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        return (
            f"Today is {date_str}, and the current local time is {time_str}. "
            f"How can I assist you with your courses, examination schedules, or university updates today?"
        )

    # 1. Pure Greeting (hi, hello, etc.)
    if RE_GREETING.match(cleaned):
        return MDU_GREETING_RESPONSE

    # 2. Identity / About (who are you, who are u, etc.)
    if RE_IDENTITY.match(cleaned):
        return MDU_IDENTITY_RESPONSE

    # 3. Capabilities / Help (what can you do, help, etc.)
    if RE_HELP.match(cleaned):
        return MDU_HELP_RESPONSE

    # 4. How are you (how are you, how are u)
    if RE_HOW_ARE_YOU.match(cleaned):
        return MDU_HOW_ARE_YOU_RESPONSE

    # 5. Gratitude (thank you, thanks)
    if RE_GRATITUDE.match(cleaned):
        return MDU_GRATITUDE_RESPONSE

    # 6. Farewell (bye, goodbye)
    if RE_FAREWELL.match(cleaned):
        return MDU_FAREWELL_RESPONSE

    return None
