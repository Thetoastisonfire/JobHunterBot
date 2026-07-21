"""Filtering rules: blacklist terms, tech relevance, years-of-experience, seniority."""
import re
from typing import Any

_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_NUM_WORD_RE = r'\b(?:\d+|' + '|'.join(_WORD_TO_NUM.keys()) + r')\b'

SENIOR_TITLE_RE = re.compile(
    r'\b(senior|sr\.?|lead|principal|staff\s+engineer|director|manager|'
    r'vice\s+president|\bvp\b|head\s+of)\b', re.I
)

# Requires the job to actually look like a software/dev role. Adzuna is a job
# aggregator with loose matching under the hood (its "phrase match" behavior
# isn't officially documented), so completely unrelated listings sometimes
# come back for a tech search. This is a client-side backstop: if neither the
# title nor description contains any recognizable tech/dev term, reject it
# regardless of what Adzuna's own matching decided.
TECH_RELEVANCE_RE = re.compile(
    r'\b(developer|engineer|programmer|software|swe|full[\s-]?stack|'
    r'front[\s-]?end|back[\s-]?end|application develop|dev\b|coding|'
    r'\.net|devops|cloud engineer|data engineer|qa engineer|sde\b)\b', re.I
)


def _to_num(s: str) -> int:
    s = s.strip().lower()
    if s in _WORD_TO_NUM:
        return _WORD_TO_NUM[s]
    return int(s) if s.isdigit() else 0


def max_years_in_text(text: str) -> int:
    """Return the highest year requirement found in text, or 0 if none."""
    t = text.lower()
    best = 0
    # "5+ years experience", "5 years of experience", "5 years exp"
    for m in re.finditer(r'(\d+)\+?\s*(?:-\s*\d+\s*)?years?\s*(?:of\s*)?(?:experience|exp\b)', t):
        best = max(best, int(m.group(1)))
    # "minimum 5 years", "at least 3 years", "requires 4 years"
    for m in re.finditer(r'(?:minimum|at least|requires?)\s+(\d+)\+?\s*years?', t):
        best = max(best, int(m.group(1)))
    # "5-8 years of experience", "5 to 8 years experience" (range before the word "years")
    for m in re.finditer(r'(\d+)\s*(?:-|–|to)\s*\d+\s*years?\s*(?:of\s*)?(?:experience|exp\b)', t):
        best = max(best, int(m.group(1)))
    # "experience range - 6 to 10 years", "experience: 3-5 years" (word "experience" comes first)
    for m in re.finditer(r'experience\s*(?:range|level)?\s*[:\-–]?\s*(\d+)\s*(?:\+|-|–|to)?\s*\d*\s*years?', t):
        best = max(best, int(m.group(1)))
    # Spelled-out numbers: "five or more years", "three-plus years", "at least seven years"
    _lead_num_re = r'\d+|' + '|'.join(_WORD_TO_NUM.keys())
    for m in re.finditer(_NUM_WORD_RE + r'(?:\s+or\s+more|\+|-plus)?\s*years?\s*(?:of\s*)?(?:experience|exp\b)?', t):
        lead = re.match(_lead_num_re, m.group(0))
        if lead:
            n = _to_num(lead.group(0))
            if n:
                best = max(best, n)
    for m in re.finditer(r'(?:minimum|at least|requires?)\s+' + _NUM_WORD_RE + r'\s*(?:\+|-plus)?\s*years?', t):
        sub = re.search(_NUM_WORD_RE, m.group(0))
        if sub:
            n = _to_num(sub.group(0))
            best = max(best, n)
    return best


def should_filter(job: dict[str, Any], blacklist: list[str], max_years: int) -> tuple[bool, str]:
    """Returns (filter_out, reason). Checks blacklist then experience."""
    company = job.get("company", "").lower()
    title   = job.get("title",   "").lower()
    desc    = job.get("excerpt", "").lower()

    # -- Blacklist (checked against company, title, and description) --
    # Word-boundary matching, not raw substring: a single-word term like
    # "sales" would otherwise match inside unrelated words/company names
    # such as "Salesforce" (a CRM tool mentioned in tons of unrelated
    # software job postings). Multi-word phrases (e.g. "security clearance")
    # still match as phrases.
    haystack = " ".join([company, title, desc])
    for b in blacklist:
        if re.search(r'\b' + re.escape(b) + r'\b', haystack):
            return True, "blacklisted term: " + b

    # -- Relevance check: must actually look like a tech/dev role --
    if not TECH_RELEVANCE_RE.search(title + " " + desc):
        return True, "not a tech/dev role: " + job["title"]

    # -- Experience filter (skip if max_years == 0) --
    if max_years > 0:
        years = max_years_in_text(title + " " + desc)
        if years > max_years:
            return True, str(years) + "+ yrs required (max " + str(max_years) + ")"

        # For entry-level settings (<= 2 yrs), also block obvious senior titles.
        # Checked against title AND the first part of the description, since
        # a posting's true title (e.g. "Senior Big Data Engineer") sometimes
        # only appears restated at the start of the description text, while
        # Adzuna's separate "title" field shows a shortened version.
        senior_check_text = title + " " + desc[:80]
        if max_years <= 2 and SENIOR_TITLE_RE.search(senior_check_text):
            return True, "senior title: " + job["title"]

    return False, ""
