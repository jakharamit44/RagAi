import re
from typing import Optional

# ---------------------------------------------------------------------------
# Official English Responses (MDU Rohtak Academic Assistant)
# ---------------------------------------------------------------------------
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
    "• University admission guidelines, portals, and deadlines\n"
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

# ---------------------------------------------------------------------------
# Official Hindi & Hinglish Responses (MDU Rohtak Academic Assistant)
# ---------------------------------------------------------------------------
MDU_GREETING_RESPONSE_HINDI = (
    "नमस्ते! मैं महर्षि दयानंद विश्वविद्यालय (MDU), रोहतक का आधिकारिक AI अकादमिक सहायक (AI Academic Assistant) हूँ। "
    "आज मैं आपके कोर्स, सिलेबस, परीक्षा डेटशीट, एडमिशन या विश्वविद्यालय के नियमों से संबंधित प्रश्नों में आपकी क्या सहायता कर सकता हूँ?"
)

MDU_IDENTITY_RESPONSE_HINDI = (
    "नमस्ते! मैं महर्षि दयानंद विश्वविद्यालय (MDU), रोहतक का आधिकारिक AI अकादमिक सहायक (AI Academic Assistant) हूँ।\n\n"
    "मैं छात्रों और शिक्षकों को विश्वविद्यालय के आधिकारिक दस्तावेज़ों—जैसे कोर्स सिलेबस, परीक्षा डेटशीट, एडमिशन प्रक्रिया, "
    "अकादमिक काउंसिल के निर्णय और नोटिफिकेशन्स—की सटीक और सत्यापित जानकारी खोजने में मदद करता हूँ।\n\n"
    "आज मैं आपकी क्या सहायता कर सकता हूँ?"
)

MDU_HELP_RESPONSE_HINDI = (
    "मैं महर्षि दयानंद विश्वविद्यालय (MDU), रोहतक से संबंधित सत्यापित जानकारियों में आपकी सहायता कर सकता हूँ, जैसे:\n"
    "• कोर्स सिलेबस, क्रेडिट्स, विषय और शिक्षक विवरण\n"
    "• परीक्षा डेटशीट, समय-सारणी और परीक्षा केंद्र के दिशानिर्देश\n"
    "• एडमिशन प्रक्रिया, कट-ऑफ, पात्रता और अंतिम तिथियाँ\n"
    "• यूनिवर्सिटी के आधिकारिक नोटिफिकेशन्स और नियम\n"
    "• परीक्षा हॉल में कैलकुलेटर और गैजेट्स के नियम\n\n"
    "आप किस विषय में जानकारी चाहते हैं?"
)

MDU_HOW_ARE_YOU_RESPONSE_HINDI = (
    "मैं बहुत अच्छा हूँ, पूछने के लिए धन्यवाद! मैं MDU रोहतक से संबंधित आपके किसी भी अकादमिक प्रश्न या जानकारी के लिए तैयार हूँ। "
    "आज मैं आपकी क्या मदद कर सकता हूँ?"
)

MDU_GRATITUDE_RESPONSE_HINDI = (
    "आपका बहुत-बहुत स्वागत है! यदि आपके पास पढ़ाई, सिलेबस या विश्वविद्यालय के नए अपडेट्स से संबंधित कोई और प्रश्न हो, "
    "तो बेझिझक पूछें। MDU रोहतक में आपकी पढ़ाई और परीक्षाओं के लिए हार्दिक शुभकामनाएँ!"
)

MDU_FAREWELL_RESPONSE_HINDI = (
    "अलविदा! आपका दिन शुभ हो और महर्षि दयानंद विश्वविद्यालय (MDU), रोहतक में आपकी पढ़ाई सफल रहे। "
    "जब भी कोई सहायता चाहिए हो, आप यहाँ कभी भी पूछ सकते हैं!"
)

# ---------------------------------------------------------------------------
# Language Detection Helper
# ---------------------------------------------------------------------------
HINGLISH_MARKERS = {
    "tum", "aap", "tu", "kon", "kaun", "kya", "kab", "kahan", "kaha", "kaise", "kese",
    "kyun", "kyu", "hai", "hain", "ho", "hu", "hoon", "tera", "teri", "tere", "tumhara",
    "tumhari", "tumhare", "aapka", "aapki", "aapke", "mera", "meri", "mere", "apna", "apne",
    "apni", "naam", "nam", "batao", "bataiye", "bata", "bhai", "karo", "karein", "chahiye",
    "milega", "milegi", "milenge", "hoga", "hogi", "honge", "liye", "pariksha", "dakhila",
    "aaj", "tarikh", "tithi", "shukriya", "dhanyawad", "namaste", "namaskar", "pranam",
    "alvida", "chal", "kuch", "bataye", "dijiye", "samay", "din", "kripya", "theek",
    "badhiya", "kare", "fir", "phir", "pe", "se", "ko"
}

def is_hindi_or_hinglish(text: str) -> bool:
    """
    Detects if the query is in Hindi (Devanagari script) or Hinglish (Hindi written in Roman script).
    """
    if not text:
        return False

    # 1. Check for Devanagari Unicode characters (\u0900-\u097F)
    if re.search(r"[\u0900-\u097F]", text):
        return True

    # 2. Check for common Hinglish marker words
    words = set(re.findall(r"\b[a-zA-Z]{2,}\b", text.lower()))
    if words & HINGLISH_MARKERS:
        return True

    return False


# ---------------------------------------------------------------------------
# Multilingual Intent Regex Patterns
# ---------------------------------------------------------------------------
RE_GREETING = re.compile(
    r"^(?:"
    r"hi|hello|hey|heya|hlo|namaste|namastey|namaskar|namaskaar|pranam|pranaam|ram\s*ram|radhe\s*radhe|jai\s*shree\s*ram|"
    r"good\s+(?:morning|afternoon|evening|day)|greetings?|"
    r"नमस्ते|नमस्कार|प्रणाम|राम\s*राम|राधे\s*राधे|जय\s*श्री\s*राम"
    r")(?:\s+there|\s+assistant|\s+ai|\s+bot|\s+ji|\s+bhai|\s+sir|\s+mam)?[\s!.,?]*$",
    re.IGNORECASE
)

RE_IDENTITY = re.compile(
    r"^(?:"
    r"who\s+(?:are\s+you|are\s+u|r\s+u|developed\s+you|made\s+you|created\s+you)|"
    r"what\s+(?:are\s+you|is\s+your\s+name|is\s+this\s+ai|is\s+this\s+bot|is\s+this\s+system)|"
    r"introduce\s+(?:yourself|urself)|tell\s+me\s+about\s+(?:yourself|urself)|"
    r"which\s+(?:university\s+are\s+you\s+for|ai\s+is\s+this|university|college)|"
    # Hinglish identity patterns
    r"(?:tum|aap|tu)\s+(?:kon|kaun)\s+(?:ho|hain|h|hai)|"
    r"(?:kon|kaun)\s+(?:ho|hai|h)\s+(?:tum|aap|tu)|"
    r"(?:tumhara|aapka|tera)\s+naam\s+kya\s+(?:hai|h)|"
    r"kya\s+naam\s+(?:hai|h)\s+(?:tumhara|aapka|tera)|"
    r"(?:tum|aap)\s+kya\s+(?:ho|hain|hai)|"
    r"apna\s+parichay\s+(?:do|dijiye)|apne\s+ba?re\s+me(?:in)?\s+batao|"
    # Devanagari identity patterns
    r"तुम\s+कौन\s+हो|आप\s+कौन\s+हैं|आप\s+कौन\s+हो|तुम्हारा\s+नाम\s+क्या\s+है|आपका\s+नाम\s+क्या\s+है|अपना\s+परिचय\s+दो|अपने\s+बारे\s+में\s+बताओ"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

RE_HELP = re.compile(
    r"^(?:"
    r"what\s+can\s+you\s+do|how\s+can\s+you\s+help(?:\s+me)?|what\s+do\s+you\s+do|help(?:\s+me)?|capabilities|"
    # Hinglish help patterns
    r"(?:tum|aap)?\s*kya\s+kar\s+sakte\s+(?:ho|hain)|"
    r"kya\s+(?:madad|help)\s+kar\s+sakte\s+(?:ho|hain)|"
    r"(?:madad|help)\s+(?:karo|chahiye|dijiye)|"
    # Devanagari help patterns
    r"तुम\s+क्या\s+कर\s+सकते\s+हो|आप\s+क्या\s+कर\s+सकते\s+हैं|मेरी\s+मदद\s+करो|सहायता\s+चाहिए"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

RE_HOW_ARE_YOU = re.compile(
    r"^(?:"
    r"how\s+(?:are\s+you|are\s+u|r\s+u)|how\'?s\s+it\s+going|how\s+do\s+you\s+do|"
    # Hinglish patterns
    r"(?:aap|tum)?\s*(?:kaise|kese)\s+(?:ho|hain)|"
    r"kya\s+haal\s+(?:hai|chaal|h)|"
    r"kya\s+chal\s+raha\s+(?:hai|h)|"
    r"sab\s+(?:theek|badhiya)|"
    # Devanagari patterns
    r"आप\s+कैसे\s+हैं|कैसे\s+हो|क्या\s+हाल\s+है"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

RE_GRATITUDE = re.compile(
    r"^(?:"
    r"thanks?|thank\s+you(?:\s+very\s+much)?|thank\s+u|thx|tysm|ok\s+thanks?|okay\s+thanks?|"
    # Hinglish
    r"dhanyawad|dhanyavaad|shukriya(?:\s+ji)?|bahut\s+(?:bahut\s+)?(?:dhanyawad|shukriya)|thanks\s+(?:bhai|ji)|thank\s+you\s+(?:bhai|ji)|"
    # Devanagari
    r"धन्यवाद|शुक्रिया|बहुत\s+बहुत\s+धन्यवाद"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

RE_FAREWELL = re.compile(
    r"^(?:"
    r"bye|goodbye|see\s+you|cya|see\s+ya|have\s+a\s+good\s+day|"
    # Hinglish
    r"alvida|phir\s+milenge|fir\s+milenge|chalta\s+hu|chalte\s+hain|bye\s+bhai|"
    # Devanagari
    r"अलविदा|फिर\s+मिलेंगे"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

RE_DATETIME = re.compile(
    r"^(?:"
    r"what\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:date|time|day|datetime|date\s+and\s+time|today\'?s?\s+date)|"
    r"current\s+(?:date(?:\s+(?:and|&)\s+time)?|time|datetime)|"
    r"today\'?s?\s+(?:date|day)|"
    r"date\s+(?:and|&)\s+time|"
    r"what\s+day\s+is\s+it|what\s+time\s+is\s+it|what\s+is\s+today|"
    # Hinglish
    r"aaj\s+(?:kaun\s*si|konsi|kya)\s+(?:date|tarikh|tithi)\s+(?:hai|h)|"
    r"aaj\s+ki\s+(?:date|tarikh|tithi)|"
    r"(?:time|samay)\s+kya\s+(?:hua\s+hai|hai|h)|"
    r"aaj\s+kya\s+(?:din|vaar)\s+hai|"
    # Devanagari
    r"आज\s+क्या\s+तारीख\s+है|आज\s+कौन\s*सी\s+तारीख\s+है|आज\s+क्या\s+दिन\s+है|समय\s+क्या\s+हुआ\s+है"
    r")[\s!.,?]*$",
    re.IGNORECASE
)

def get_conversational_response(question: str) -> Optional[str]:
    """
    Checks if the user's input is a pure conversational query (greeting, identity, date/time, gratitude, etc.).
    Returns a natural, friendly response as the MDU Rohtak University AI Assistant in the user's language (Hindi/Hinglish/English),
    or None if the query contains domain-specific academic questions requiring RAG retrieval.
    """
    if not question:
        return MDU_GREETING_RESPONSE

    cleaned = question.strip()
    is_hindi = is_hindi_or_hinglish(cleaned)

    # 0. Current Date / Time Inquiry
    if RE_DATETIME.match(cleaned):
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        if is_hindi:
            return (
                f"आज {date_str} है, और वर्तमान स्थानीय समय {time_str} है। "
                f"आज मैं महर्षि दयानंद विश्वविद्यालय (MDU), रोहतक से संबंधित आपके कोर्स, परीक्षा या अन्य जानकारियों में क्या सहायता कर सकता हूँ?"
            )
        return (
            f"Today is {date_str}, and the current local time is {time_str}. "
            f"How can I assist you with your courses, examination schedules, or university updates today?"
        )

    # 1. Pure Greeting (hi, hello, namaste, etc.)
    if RE_GREETING.match(cleaned):
        return MDU_GREETING_RESPONSE_HINDI if is_hindi else MDU_GREETING_RESPONSE

    # 2. Identity / About (who are you, tum kon ho, aap kaun ho, etc.)
    if RE_IDENTITY.match(cleaned):
        return MDU_IDENTITY_RESPONSE_HINDI if is_hindi else MDU_IDENTITY_RESPONSE

    # 3. Capabilities / Help (what can you do, kya kar sakte ho, etc.)
    if RE_HELP.match(cleaned):
        return MDU_HELP_RESPONSE_HINDI if is_hindi else MDU_HELP_RESPONSE

    # 4. How are you (how are you, kaise ho, etc.)
    if RE_HOW_ARE_YOU.match(cleaned):
        return MDU_HOW_ARE_YOU_RESPONSE_HINDI if is_hindi else MDU_HOW_ARE_YOU_RESPONSE

    # 5. Gratitude (thank you, dhanyawad, shukriya, etc.)
    if RE_GRATITUDE.match(cleaned):
        return MDU_GRATITUDE_RESPONSE_HINDI if is_hindi else MDU_GRATITUDE_RESPONSE

    # 6. Farewell (bye, alvida, phir milenge, etc.)
    if RE_FAREWELL.match(cleaned):
        return MDU_FAREWELL_RESPONSE_HINDI if is_hindi else MDU_FAREWELL_RESPONSE

    return None
