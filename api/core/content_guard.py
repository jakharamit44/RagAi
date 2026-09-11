"""
api/core/content_guard.py
Enterprise AI Safety Governor & Content Moderation Engine for Indian Higher Education.

Guards against:
1. Profanity, vulgarities, and abusive language across Hindi, Hinglish, and English.
2. Communal, religious, and casteist hate speech (prohibited under BNS/IPC and SC/ST PoA Act).
3. Adversarial "AI Teaching", model poisoning, and persona hijacking ("learn that...", "ab se yeh maanoge...").
4. Academic dishonesty (cheating, exam chits/farre, paper leaks, degree/marksheet forgery, portal tampering).
5. UGC Anti-Ragging violations and campus harassment.
6. Feedback loop and self-improvement prompt poisoning.

Includes contextual whitelisting for legitimate academic inquiries (e.g., anti-ragging committee, UMC penalties).
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any


@dataclass
class SafetyInspectionResult:
    is_safe: bool
    category: Optional[str] = None
    severity: str = "LOW"
    matched_snippet: Optional[str] = None
    user_message: Optional[str] = None
    action: str = "ALLOW"


# ==============================================================================
# 1. TEXT NORMALIZATION ENGINE
# ==============================================================================

# Common character substitutions used by attackers to evade keyword filters
LEET_MAP = {
    '@': 'a', '4': 'a', '8': 'b', '(': 'c', '<': 'c', '3': 'e',
    '1': 'i', '!': 'i', '|': 'i', '0': 'o', '$': 's', '5': 's',
    '7': 't', '+': 't', 'v': 'u',
}

def normalize_text(text: str) -> str:
    """
    Cleans, squashes leetspeak, collapses repeated characters, and removes
    intra-word evasion symbols (e.g. 'chuuuutttiiyaaa' -> 'chutiya', 'b.c' -> 'bc').
    """
    if not text or not isinstance(text, str):
        return ""

    # Unicode normalization (NFKD decomposes ligatures and combined accents)
    normalized = unicodedata.normalize("NFKD", text).strip()
    
    # Lowercase
    lower_text = normalized.lower()

    # Remove zero-width spaces and non-printable control characters
    lower_text = re.sub(r"[\u200B-\u200D\uFEFF]", "", lower_text)

    # Collapse consecutive identical characters to at most 2 (e.g. 'bheeencchhhooood' -> 'bhenchod')
    collapsed = re.sub(r"(.)\1{2,}", r"\1\1", lower_text)

    return collapsed


def get_squashed_text(text: str) -> str:
    """
    Generates a version with punctuation, spaces, and intra-word separators stripped
    to catch evasions like 'b h e n c h o d', 'b.c.', 'c_h_u_t_i_y_a'.
    """
    normalized = normalize_text(text)
    # Map leetspeak characters
    mapped = "".join(LEET_MAP.get(ch, ch) for ch in normalized)
    # Remove all non-alphanumeric characters (keeping Devanagari and Latin letters/digits)
    squashed = re.sub(r"[^\w\u0900-\u097F]", "", mapped)
    # Collapse repeat characters down to 1 in squashed form for aggressive matching
    return re.sub(r"(.)\1+", r"\1", squashed)


# ==============================================================================
# 2. THREAT CATEGORY DEFINITIONS & REGEX PATTERNS
# ==============================================================================

# --- Category 1: Profanity, Vulgarity & Abuse (Hindi, Hinglish, English) ---
PROFANITY_HINDI_HINGLISH_PATTERNS = [
    # Common Hindi/Hinglish mother/sister expletives & abbreviations (bc, mc, etc.)
    r"\b(b\.?c\.?|b\*c|bhenchod|behenchod|bhen\s*chod|behen\s*chod|bhenke\s*lode|bhenchodd)\b",
    r"\b(m\.?c\.?|m\*c|madarchod|madar\s*chod|maarchod|madarchodd)\b",
    r"\b(bhosdike|bhosadi|bhosadike|bhosdi|bhosdk|bhosd|bsdk|b\.?s\.?d\.?k)\b",
    r"\b(chutiya|chutiye|chutye|chootiya|chut\*ya|ch\*tiya|chutiyapa)\b",
    r"\b(gandu|gaand|g@ndu|gandwa|gandfat|gandmasti)\b",
    r"\b(lauda|loda|lode|laude|l0da|laude\s*lag\s*gaye)\b",
    r"\b(harami|haramkhor|haramzada|haramzade)\b",
    r"\b(randi|rand|randi\s*rona|raand)\b",
    r"\b(kamine|kamina|kaminey|kutti\s*kamini)\b",
    r"\b(saale|saali|bhadwe|bhadwa|chhed|chodu)\b",
    r"\b(teri\s*maa\s*ki|maa\s*ki\s*chut|tere\s*baap\s*ka)\b",
    # Devanagari script profanity (supports decomposed unicode & nukta variations)
    r"(बहनचोद|मादरचोद|भोस[डड़\u093c]*ीके?|भोस[डड़\u093c]*ी|चूतिया|गांडू|हरामी|हराम[जज़\u093c]*ादा|लौ[डड़\u093c]*ा|लवड़े|रंडी|कमीने|साले|भा[डड़\u093c]*वे)",
]

PROFANITY_ENGLISH_PATTERNS = [
    r"\b(f+u+c+k|f\*ck|f\*\*k|fucking|fucker|motherfucker|mf)\b",
    r"\b(b+i+t+c+h|b\*tch|b!tch|bitches)\b",
    r"\b(a+s+s+h+o+l+e|a\*\*hole|dumbass|jackass)\b",
    r"\b(b+a+s+t+a+r+d|bastards)\b",
    r"\b(c+u+n+t|d+i+c+k|p+u+s+s+y|d+i+l+d+o)\b",
    r"\b(w+h+o+r+e|s+l+u+t|f+a+g+g+o+t|r+e+t+a+r+d)\b",
    r"\b(go\s+die|kill\s+yourself|kys)\b",
]

# --- Category 2: Communal, Casteist & Religious Hate Speech (Indian Legal Guard) ---
HATE_SPEECH_PATTERNS = [
    # Casteist slurs prohibited by the SC/ST (Prevention of Atrocities) Act
    r"\b(bhangi|chamar|chura|neech\s*jaati|achhut|chandal)\b",
    # Communal hatred / inciting religious violence
    r"(?i)\b(dange\s*karwao|rioting|burn\s*the\s*temple|burn\s*the\s*mosque|kill\s*all\s*(hindus|muslims|sikhs|christians))\b",
    r"(?i)\b(terrorist\s*(religion|community)|jihadi\s*dog|kafir\s*maro)\b",
]

# --- Category 3: Adversarial "AI Teaching", Model Poisoning & Persona Hijacking ---
ADVERSARIAL_TEACHING_PATTERNS = [
    # Coercive teaching / forcing AI to adopt bad beliefs or fake rules
    r"(?i)\b(learn\s+that|remember\s+that|accept\s+as\s+(a\s+)?fact|believe\s+that|update\s+your\s+knowledge)\b.*\b(cheating|cheat|allowed|fake|corrupt|briber?y?|bribes?|paying\s+bribes?|illegal|hack|hacked)\b",
    r"(?i)\b(from\s+now\s+on\s+you\s+(believe|think|must\s+say|will\s+teach|answer))\b",
    r"(?i)\b(i\s+am\s+(teaching|educating|programming|reprogramming)\s+you\s+that)\b",
    r"(?i)\b(forget\s+(what\s+)?(university|ugc|mdu|management|rules|guidelines)\s+(said|stated|told))\b",
    r"(?i)\b(tumhe\s+(sikhna|yaad\s*rakhna|maanna)\s+hoga\s+ki)\b",
    r"(?i)\b(aaj\s+se\s+(tum\s+)?(yeh\s+)?(maanoge|sikhoge|bologe)\s+ki)\b",
    r"(?i)\b(ab\s+se\s+tumhara\s+naya\s+rule\s+hai)\b",
    r"(?i)\b(tujhe\s+mai\s+sikha\s+raha\s+hu)\b",
    r"(?i)\b(adopt\s+this\s+(belief|rule|axiom|command))\b",
    # Persona hijacking to act unethically or illegally
    r"(?i)\b(act\s+as|pretend\s+to\s+be|behave\s+as)\s+(an?\s+)?(evil|unrestricted|unfiltered|corrupt|criminal|hacker|unethical)\b",
    r"(?i)\b(dan\s+mode|developer\s+mode\s+enabled|jailbreak\s+activated|bypass\s+all\s+rules)\b",
]

# --- Category 4: Academic Malpractice & Examination Cheating (UMC & Forgery) ---
ACADEMIC_MALPRACTICE_PATTERNS = [
    # Exam cheating instructions (chits, farre, smuggling, phones, bluetooth)
    r"(?i)\b(how\s+to|kese|kaise)\b.*\b(cheat|carry\s+chits?|hide\s+chits?|(bring|hide|sneak|use|carry)\s+(phone|mobile|bluetooth|device|chits?)|nakal|chori)\b.*\b(exam|examination|paper|hall|center|centre)\b",
    r"(?i)\b(exam|examination|paper|hall)\b.*\b(cheating|chits?|farre?|nakal)\b.*\b(kaise|kese|tarik[ae]|ideas?|trick|le\s*j[a]+ye)\b",
    r"(?i)\b(chits?|farre?|nakal)\b.*\b(kaise|kese)\s+(le\s*j[a]+ye|kare|banaye|chupaye)\b",
    r"(?i)\b(leak|leaked|leaks?)\b.*\b(paper|question\s*paper|exam)\b",
    r"(?i)\b(exam\s+)?(paper|question\s*paper)\b.*\b(leak|leaked|buy|sell|chori|kahan\s+milega)\b",
    r"(?i)\b(paper\s+leak\s+karne\s+ka\s+tarika)\b",
    r"(?i)\b(bribe|paise\s*dekar)\s+(examiner|invigilator|teacher|marks|pass)\b",
    # Degree & certificate forgery / Portal tampering
    r"(?i)\b(how\s+to|kaise)\b.*\b(forge|forging|make\s+fake|buy\s+fake|create\s+fake|tamper)\b.*\b(degree|marksheet|diploma|certificate|admit\s*card|result)\b",
    r"(?i)\b(fake|duplicate|nakli|forged?)\b.*\b(degree|marksheet|certificate|diploma)\b.*\b(kaise|kese|kahan|banaye|kharide|buy|order|sell)\b",
    r"(?i)\b(how\s+to\s+hack|hack\s+karne\s+ka\s+tarika)\b.*\b(mdu|university|result\s*portal|database|exam\s*system)\b",
]

# --- Category 5: UGC Anti-Ragging Violations & Campus Harassment ---
RAGGING_PATTERNS = [
    r"(?i)\b(how\s+to\s+rag|tips\s+for\s+ragging|ideas\s+to\s+rag|how\s+to\s+haze)\s+(juniors?|students?|freshers?)\b",
    r"(?i)\b(juniors?\s+(ki\s+ragging|ko\s+ragging)\s+(kaise|kese)\s+kare(in)?)\b",
    r"(?i)\b(ragging\s+karne\s+ke\s+(tarike|tips|ideas))\b",
    r"(?i)\b(harass|intimidate|bully|strip|beat)\s+(juniors?|freshers?|hostelers?)\b",
]

# --- Contextual Whitelist for Legitimate Regulatory / Policy Inquiries ---
# Students frequently ask about anti-ragging rules, affidavit formats, UMC penalties,
# and women's safety committees. These MUST NEVER be blocked!
LEGITIMATE_POLICY_WHITELIST = [
    r"(?i)\b(anti[\s\-]ragging|anti\s+ragging)\s+(committee|cell|helpline|affidavit|form|policy|rules?|guidelines?|declaration|undertaking|number|squad)\b",
    r"(?i)\b(ugc|university)\s+(regulations?|guidelines?)\s+(on|against)\s+ragging\b",
    r"(?i)\b(punishment|penalty|rules?|ordinance|committee)\s+(for|against|regarding|of)\s+(unfair\s+means|umc)\b",
    r"(?i)\b(umc\s+(rules?|hearing|ordinance|punishment|committee|decision))\b",
    r"(?i)\b(internal\s+complaints\s+committee|icc|women\s+safety\s+cell|posh\s+act)\b",
    r"(?i)\b(what\s+is\s+ragging|define\s+ragging|definition\s+of\s+ragging)\b",
]


# ==============================================================================
# 3. SAFETY INSPECTOR ENGINE
# ==============================================================================

def is_legitimate_policy_inquiry(text: str) -> bool:
    """
    Checks if a query mentioning sensitive academic topics (ragging, UMC, harassment)
    is a genuine informational query about university regulations, affidavits, or committees.
    """
    for pat in LEGITIMATE_POLICY_WHITELIST:
        if re.search(pat, text):
            return True
    return False


def inspect_content_safety(text: str, context: str = "query") -> SafetyInspectionResult:
    """
    Exhaustively scans text for abusive words, communal slurs, adversarial teaching,
    academic malpractice, and ragging violations.

    Parameters:
    - text: Incoming student/employee query, feedback reason, or prompt rule.
    - context: 'query' | 'feedback' | 'prompt_rule' | 'brain_probe'

    Returns:
    - SafetyInspectionResult with is_safe, category, severity, matched snippet, and bilingual refusal notice.
    """
    if not text or not isinstance(text, str):
        return SafetyInspectionResult(is_safe=True)

    normalized = normalize_text(text)
    squashed = get_squashed_text(text)

    # --------------------------------------------------------------------------
    # 1. Check for Profanity / Abusive Language (Highest Priority)
    # --------------------------------------------------------------------------
    # Check Hindi/Hinglish profanity patterns
    for pat in PROFANITY_HINDI_HINGLISH_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE) or re.search(pat, text, re.IGNORECASE)
        if m:
            return SafetyInspectionResult(
                is_safe=False,
                category="PROFANITY_ABUSE",
                severity="HIGH",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Your request was blocked because it contains abusive, offensive, or vulgar language. "
                    "All interactions on the university portal must adhere to institutional conduct standards.\n\n"
                    "आपका अनुरोध ब्लॉक कर दिया गया है क्योंकि इसमें अपमानजनक या अनुचित भाषा का प्रयोग किया गया है। "
                    "विश्वविद्यालय पोर्टल पर शालीनता और आचार संहिता का पालन अनिवार्य है।"
                )
            )

    # Check English profanity patterns
    for pat in PROFANITY_ENGLISH_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            return SafetyInspectionResult(
                is_safe=False,
                category="PROFANITY_ABUSE",
                severity="HIGH",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Your request was blocked because it contains profanity or offensive language. "
                    "Please maintain professional and respectful academic communication."
                )
            )

    # Check squashed text for obfuscated profanities (e.g. 'b.h.e.n.c.h.o.d', 'bhosdk')
    squashed_profanities = ["bhenchod", "behenchod", "madarchod", "bhosdike", "bhosdi", "chutiya", "gandu", "lauda", "loda", "fuck", "bitch", "cunt"]
    for word in squashed_profanities:
        if word in squashed:
            return SafetyInspectionResult(
                is_safe=False,
                category="PROFANITY_ABUSE",
                severity="HIGH",
                matched_snippet=word,
                action="BLOCK",
                user_message=(
                    "Your request was blocked due to detected abusive language or evasive profanity. "
                    "University systems strictly prohibit profanity in both English and regional dialects."
                )
            )

    # --------------------------------------------------------------------------
    # 2. Check for Casteist, Communal & Religious Hate Speech
    # --------------------------------------------------------------------------
    for pat in HATE_SPEECH_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            return SafetyInspectionResult(
                is_safe=False,
                category="HATE_SPEECH_COMMUNAL",
                severity="CRITICAL",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Your request was blocked because it contains prohibited casteist, communal, or hate speech. "
                    "Such statements violate Indian legal provisions (SC/ST PoA Act and BNS/IPC) and university regulations.\n\n"
                    "यह अनुरोध अवरुद्ध कर दिया गया है क्योंकि इसमें गैर-कानूनी जातिगत, सांप्रदायिक या घृणास्पद भाषा का प्रयोग है।"
                )
            )

    # --------------------------------------------------------------------------
    # 3. Check for Adversarial "AI Teaching", Brainwashing & Model Poisoning
    # --------------------------------------------------------------------------
    for pat in ADVERSARIAL_TEACHING_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            return SafetyInspectionResult(
                is_safe=False,
                category="ADVERSARIAL_TEACHING",
                severity="HIGH",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Your request was blocked because it attempts to instruct, reprogram, or force custom beliefs onto the AI assistant. "
                    "The AI Academic Assistant is governed strictly by verified university circulars and official syllabus data, "
                    "and cannot be taught or reconfigured by end users.\n\n"
                    "आपका अनुरोध अस्वीकार कर दिया गया है क्योंकि इसमें एआई को अनधिकृत निर्देश या गलत जानकारी सिखाने का प्रयास किया गया है।"
                )
            )

    # --------------------------------------------------------------------------
    # 4. Check for UGC Anti-Ragging & Campus Harassment (with Whitelist)
    # --------------------------------------------------------------------------
    for pat in RAGGING_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            # Verify if this is a legitimate inquiry about anti-ragging committee or rules
            if is_legitimate_policy_inquiry(text):
                continue

            return SafetyInspectionResult(
                is_safe=False,
                category="RAGGING_HARASSMENT",
                severity="CRITICAL",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Ragging is a punishable criminal offence under UGC Anti-Ragging Regulations and orders of the Hon'ble Supreme Court of India. "
                    "Any query promoting or seeking advice on ragging juniors is strictly blocked and logged for institutional review. "
                    "If you are a victim of ragging, please contact the MDU Anti-Ragging Helpline or email antiragging@mdurohtak.ac.in.\n\n"
                    "रैगिंग माननीय सर्वोच्च न्यायालय और यूजीसी नियमों के तहत एक दंडनीय अपराध है। रैगिंग को बढ़ावा देने वाला कोई भी प्रश्न पूर्णतः प्रतिबंधित है।"
                )
            )

    # --------------------------------------------------------------------------
    # 5. Check for Academic Dishonesty, Exam Malpractice & Forgery (with Whitelist)
    # --------------------------------------------------------------------------
    for pat in ACADEMIC_MALPRACTICE_PATTERNS:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            # Verify if student is inquiring about UMC penalties / exam ordinances
            if is_legitimate_policy_inquiry(text):
                continue

            return SafetyInspectionResult(
                is_safe=False,
                category="ACADEMIC_MALPRACTICE",
                severity="HIGH",
                matched_snippet=m.group(0),
                action="BLOCK",
                user_message=(
                    "Your request was blocked because it seeks instructions for examination malpractice (cheating, paper leaks), "
                    "document forgery, or unauthorized system access. Academic dishonesty is subject to strict disciplinary action under university ordinances.\n\n"
                    "परीक्षा में अनुचित साधन (UMC), नकल, पेपर लीक या फर्जी डिग्री/अंकतालिका से संबंधित प्रश्न विश्वविद्यालय नियमों के तहत सख्त वर्जित हैं।"
                )
            )

    # --------------------------------------------------------------------------
    # 6. Context-Specific Validation (Feedback & Prompt Rules)
    # --------------------------------------------------------------------------
    if context == "feedback":
        # In feedback reasons, check for prompt injection or system override attempts
        feedback_override_patterns = [
            r"(?i)\b(system\s+prompt|ignore\s+all|override\s+instructions|inject|developer\s+mode)\b",
            r"(?i)\b(from\s+now\s+on\s+say|change\s+your\s+answer\s+to|teach\s+yourself)\b"
        ]
        for pat in feedback_override_patterns:
            m = re.search(pat, normalized)
            if m:
                return SafetyInspectionResult(
                    is_safe=False,
                    category="FEEDBACK_POISONING",
                    severity="HIGH",
                    matched_snippet=m.group(0),
                    action="BLOCK",
                    user_message="Feedback contains adversarial or prohibited instructional content and was rejected."
                )

    return SafetyInspectionResult(is_safe=True, action="ALLOW")
