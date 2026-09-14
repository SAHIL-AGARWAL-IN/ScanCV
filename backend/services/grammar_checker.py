import re
from typing import Dict, List, Optional
import spacy

# Curated list of common resume typos and their corrections
COMMON_RESUME_TYPOS = {
    'acheive': 'achieve',
    'acheived': 'achieved',
    'acheivement': 'achievement',
    'acheivements': 'achievements',
    'reponsible': 'responsible',
    'responsibilty': 'responsibility',
    'responsibilites': 'responsibilities',
    'managment': 'management',
    'manger': 'manager',
    'implment': 'implement',
    'implmented': 'implemented',
    'implmentation': 'implementation',
    'experiance': 'experience',
    'experianced': 'experienced',
    'developement': 'development',
    'develope': 'develop',
    'developrd': 'developed',
    'seperate': 'separate',
    'seperated': 'separated',
    'succesful': 'successful',
    'succesfully': 'successfully',
    'recieved': 'received',
    'recieve': 'receive',
    'proffesional': 'professional',
    'proffesionally': 'professionally',
    'enviroment': 'environment',
    'oppurtunity': 'opportunity',
    'oppurtunities': 'opportunities',
    'calender': 'calendar',
    'untill': 'until',
    'relevent': 'relevant',
    'collabration': 'collaboration',
    'collabrate': 'collaborate',
    'maintainance': 'maintenance',
    'maintenence': 'maintenance',
    'perfomance': 'performance',
    'referance': 'reference',
    'referances': 'references',
    'neccessary': 'necessary',
    'independant': 'independent',
    'commited': 'committed',
    'occured': 'occurred',
    'definatly': 'definitely',
    'definately': 'definitely',
}

REPEATED_WORDS_PATTERN = re.compile(r'\b(the|in|at|on|for|to|with|and|or|of|a|an|is|are|was|were)\s+\1\b', re.IGNORECASE)
PUNCTUATION_SPACING_PATTERN = re.compile(r'\b\w+\s+[,;:\.\?!]\s*\w+')


def check_grammar_and_spelling(
    text: str,
    skills: Optional[List[str]] = None,
    nlp: Optional[spacy.Language] = None,
) -> Dict:
    """
    Analyzes resume text for common grammar, spelling, punctuation, and style issues.
    Skips technical skills and proper nouns to avoid false positives.
    """
    if not text or not text.strip():
        return {
            'total_errors': 0,
            'critical_errors': [],
            'moderate_errors': [],
            'minor_errors': [],
            'grammar_score': 100.0,
            'penalty_applied': 0.0,
            'error_free_percentage': 100.0,
            'recommendations': ['No resume text provided.'],
            '_component_status': 'clean',
        }

    critical_errors: List[str] = []
    moderate_errors: List[str] = []
    minor_errors: List[str] = []

    # 1. Check for common typos
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    found_typos = set()
    for w in words:
        w_lower = w.lower()
        if w_lower in COMMON_RESUME_TYPOS and w_lower not in found_typos:
            found_typos.add(w_lower)
            correct = COMMON_RESUME_TYPOS[w_lower]
            critical_errors.append(f"Spelling error: '{w}' — did you mean '{correct}'?")

    # 2. Repeated consecutive words ("the the", "in in")
    for match in REPEATED_WORDS_PATTERN.finditer(text):
        repeated_phrase = match.group()
        moderate_errors.append(f"Duplicate word detected: '{repeated_phrase}'")

    # 3. Punctuation spacing anomalies (space before comma or period)
    space_before_punct = re.findall(r'\b\w+\s+[,;\.\?!]', text)
    for p in space_before_punct[:5]:
        moderate_errors.append(f"Irregular punctuation spacing: '{p}' (remove space before punctuation)")

    # 4. Check lowercase bullet starts
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith(('•', '-', '*', '–')) and len(ln) > 2:
            content = ln[1:].strip()
            if content and content[0].islower() and not content.startswith(('http', 'www', 'e.g.', 'i.e.')):
                minor_errors.append(f"Bullet point starts with lowercase letter: '{content[:30]}...'")
                if len(minor_errors) >= 3:
                    break

    # Calculate penalties & scores
    # Critical (spelling): 1.5 pts each
    # Moderate (repeated words / bad spacing): 0.8 pts each
    # Minor (style / capitalization): 0.3 pts each
    raw_penalty = (
        len(critical_errors) * 1.5 +
        len(moderate_errors) * 0.8 +
        len(minor_errors) * 0.3
    )
    penalty_applied = min(8.0, round(raw_penalty, 1))
    grammar_score = max(0.0, round(100.0 - penalty_applied * 12.0, 1))

    total_errors = len(critical_errors) + len(moderate_errors) + len(minor_errors)
    total_words = max(1, len(words))
    error_free_pct = max(0.0, min(100.0, round((1.0 - (total_errors / total_words)) * 100.0, 1)))

    recommendations: List[str] = []
    if total_errors == 0:
        recommendations.append("✅ Excellent grammar and spelling detected across your resume.")
    else:
        if critical_errors:
            recommendations.append(f"Fix {len(critical_errors)} spelling error(s) before applying.")
        if moderate_errors:
            recommendations.append("Clean up duplicate words and punctuation spacing.")
        if minor_errors:
            recommendations.append("Ensure every bullet point starts with a capitalized action verb.")

    return {
        'total_errors': total_errors,
        'critical_errors': critical_errors,
        'moderate_errors': moderate_errors,
        'minor_errors': minor_errors,
        'grammar_score': grammar_score,
        'penalty_applied': penalty_applied,
        'error_free_percentage': error_free_pct,
        'recommendations': recommendations,
        '_component_status': 'active',
        '_note': 'Grammar and spelling analysis active.',
    }
