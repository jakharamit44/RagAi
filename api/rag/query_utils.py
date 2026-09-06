import re
from typing import Optional, Set, List, Tuple

ORDINAL_EXPANSIONS = {
    "1st": ["first", "1st"],
    "first": ["1st", "first"],
    "2nd": ["second", "2nd"],
    "second": ["2nd", "second"],
    "3rd": ["third", "3rd"],
    "third": ["3rd", "third"],
    "4th": ["fourth", "4th"],
    "fourth": ["4th", "fourth"],
    "5th": ["fifth", "5th"],
    "fifth": ["5th", "fifth"],
    "6th": ["sixth", "6th"],
    "sixth": ["6th", "sixth"],
    "7th": ["seventh", "7th"],
    "seventh": ["7th", "seventh"],
    "8th": ["eighth", "8th"],
    "eighth": ["8th", "eighth"],
    "9th": ["ninth", "9th"],
    "ninth": ["9th", "ninth"],
    "10th": ["tenth", "10th"],
    "tenth": ["10th", "tenth"],
}

CANONICAL_ORDINAL_MAP = {
    "1st": "1", "first": "1",
    "2nd": "2", "second": "2",
    "3rd": "3", "third": "3",
    "4th": "4", "fourth": "4",
    "5th": "5", "fifth": "5",
    "6th": "6", "sixth": "6",
    "7th": "7", "seventh": "7",
    "8th": "8", "eighth": "8",
    "9th": "9", "ninth": "9",
    "10th": "10", "tenth": "10",
}

KNOWN_ENTITIES = [
    "academic council",
    "executive council",
    "court",
    "finance committee",
    "board of studies",
    "syndicate",
    "senate",
]

OCR_CORRECTIONS = [
    (r"\bTrureday\b", "Thursday"),
    (r"\bThrusday\b", "Thursday"),
    (r"\bUmiversity\b", "University"),
    (r"\bFohtak\b", "Rohtak"),
    (r"\bRohtakl\b", "Rohtak"),
    (r"\bacadenic\b", "academic"),
    (r"\bAcaieric\b", "Academic"),
    (r"\b11-30-\s*siml\.?", "11:30 a.m."),
    (r"\b11-30\s*siml\.?", "11:30 a.m."),
    (r"\bsiml\.?\b", "a.m."),
    (r"\b3s30\s*(?:2\.n\.|p\.m\.|a\.m\.)?", "3:30 p.m."),
    (r"\b2\.n\.\b", "p.m."),
    (r"\bsersion\b", "session"),
    (r"\brlonth\b", "month"),
    (r"\bofApril\b", "of April"),
    (r"\btution\b", "tuition"),
    (r"\bStadies\b", "Studies"),
    (r"\bthich\b", "which"),
    (r"\bEhe\b", "the"),
    (r"\btheRegistrar\b", "the Registrar"),
    (r"\bkugust\b", "August"),
    (r"\btne\b", "the"),
    (r"\bTne\b", "The"),
    (r"\bCommitzee\b", "Committee"),
    (r"\bRoon\b", "Room"),
    (r"\bcr\b", "of"),
    (r"\btns\b", "the"),
    (r"\bieiical\b", "Medical"),
    (r"\bColiege\b", "College"),
    (r"\boatal\b", "Rohtak"),
    (r"\bicadeaic\b", "Academic"),
    (r"\bteeting\b", "meeting"),
    (r"\bmeetizg\b", "meeting"),
    (r"\breguested\b", "requested"),
    (r"\baf\s+Medical\b", "of Medical"),
    (r"\.\s*(Saturday|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday)", r"\1"),
]

def extract_ordinals(text: str) -> List[str]:
    """Extract all canonical ordinals ('1', '2', '3', etc.) present in text."""
    lower = text.lower()
    found = []
    # Check word tokens against known ordinal spellings
    words = re.findall(r"\b[a-z0-9]+\b", lower)
    for w in words:
        if w in CANONICAL_ORDINAL_MAP:
            val = CANONICAL_ORDINAL_MAP[w]
            if val not in found:
                found.append(val)
    # Check phrases like 'semester 3', 'sem 5', 'meeting 2'
    for match in re.finditer(r"\b(?:sem(?:ester)?|meeting|session)\s*([1-9]|10)\b", lower):
        val = match.group(1)
        if val not in found:
            found.append(val)
    return found

def extract_ordinal(text: str) -> Optional[str]:
    """Extract first canonical ordinal ('1', '2', '3', etc.) if present in text."""
    ords = extract_ordinals(text)
    return ords[0] if ords else None

def extract_entity(text: str) -> Optional[str]:
    """Extract known administrative entity if present in text."""
    lower = text.lower()
    for ent in KNOWN_ENTITIES:
        if ent in lower:
            return ent
    return None

def get_conflicting_ordinals(canonical_ords: Any) -> Set[str]:
    """Return set of ordinal tokens that conflict with the given canonical ordinal(s)."""
    if isinstance(canonical_ords, str):
        target_ords = {canonical_ords}
    elif isinstance(canonical_ords, (list, set, tuple)):
        target_ords = set(canonical_ords)
    else:
        target_ords = set()

    conflicts = set()
    for word, ord_num in CANONICAL_ORDINAL_MAP.items():
        if ord_num not in target_ords:
            conflicts.add(word)
    return conflicts

def get_conflicting_entities(canonical_entity: str) -> Set[str]:
    """Return set of entities that conflict with the canonical entity."""
    conflicts = set()
    for ent in KNOWN_ENTITIES:
        if ent != canonical_entity:
            conflicts.add(ent)
    return conflicts

def clean_ocr_text(text: str) -> str:
    """Correct frequent OCR scanner distortions in archival text."""
    cleaned = text
    for pattern, replacement in OCR_CORRECTIONS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    # Remove weird multi-dash / underscore artifacts
    cleaned = re.sub(r"_+", " ", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


QUERY_TYPO_CORRECTIONS = [
    (r"\badminssion\b", "admission"),
    (r"\baddmission\b", "admission"),
    (r"\badmision\b", "admission"),
    (r"\badmisn\b", "admission"),
    (r"\buniverisyt\b", "university"),
    (r"\bunivercity\b", "university"),
    (r"\buniversty\b", "university"),
    (r"\buniv\b", "university"),
    (r"\bproccess\b", "process"),
    (r"\bproces\b", "process"),
    (r"\bsylabus\b", "syllabus"),
    (r"\bsyllubus\b", "syllabus"),
    (r"\bcours\b", "course"),
    (r"\bcorse\b", "course"),
    (r"\bfee\s+structur\b", "fee structure"),
    (r"\bfee\s+structre\b", "fee structure"),
    (r"\beligiblity\b", "eligibility"),
    (r"\beliigibility\b", "eligibility"),
    (r"\bfaclty\b", "faculty"),
    (r"\bregistr\b", "registrar"),
    (r"\bregstrar\b", "registrar"),
    (r"\bcounsil\b", "council"),
    (r"\bconcil\b", "council"),
    (r"\bschedul\b", "schedule"),
    (r"\bschedual\b", "schedule"),
    (r"\bnotifcation\b", "notification"),
    (r"\bnotifaction\b", "notification"),
    (r"\bacadamics?\b", "academic"),
]

def normalize_query(query: str) -> str:
    """Correct frequent student typos in queries before vector and keyword retrieval."""
    if not query or not isinstance(query, str):
        return query
    normalized = query
    for pattern, replacement in QUERY_TYPO_CORRECTIONS:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized

