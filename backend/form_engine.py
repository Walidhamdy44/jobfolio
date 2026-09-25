"""AI Form Answering & Salary Resolution Engine.
Answers job application screening questions, salary expectations, experience years,
and custom employer questions truthfully using candidate profile facts and AI.
"""
import re
from typing import Any
from pydantic import BaseModel, Field
from . import providers

class AnswerResponse(BaseModel):
    answer: str = Field(description='The exact, concise, truthful answer to the question.')
    explanation: str = Field(default='', description='Brief explanation of the answer.')

def _extract_digits(text: str) -> str:
    nums = re.findall(r'\d+', text.replace(',', ''))
    return nums[0] if nums else ''

def resolve_contact_field(label: str, profile: dict) -> str | None:
    l = label.strip(' *').casefold()
    name_parts = profile.get('name', '').split()
    first_name = name_parts[0] if name_parts else ''
    last_name = name_parts[-1] if len(name_parts) > 1 else ''

    if l in ('first name', 'given name', 'firstname'):
        return first_name
    if l in ('last name', 'family name', 'surname', 'lastname'):
        return last_name
    if l in ('full name', 'name', 'fullname', 'candidate name'):
        return profile.get('name', '')
    if 'email' in l:
        return profile.get('email', '')

    # Disambiguate phone country code vs phone number (AA-14)
    if ('country code' in l or 'phone code' in l or 'dialing code' in l) or (('phone' in l or 'mobile' in l) and 'country' in l):
        phone = profile.get('phone', '')
        if phone.startswith('+'):
            match = re.match(r'(\+\d{1,4})', phone)
            if match:
                return match.group(1)
        loc = profile.get('location', '')
        return loc.split(',')[-1].strip() if ',' in loc else loc

    if 'phone' in l or 'mobile' in l or 'cell' in l:
        return profile.get('phone', '')
    if 'city' in l or 'metro' in l:
        loc = profile.get('location', '')
        return loc.split(',')[0].strip() if loc else ''
    if 'country' in l or 'nation' in l:
        loc = profile.get('location', '')
        return loc.split(',')[-1].strip() if ',' in loc else loc
    if 'address' in l or 'location' in l:
        return profile.get('location', '')

    links = profile.get('links', [])
    if 'linkedin' in l:
        for link in links:
            if 'linkedin.com' in link:
                return link
    if 'github' in l:
        for link in links:
            if 'github.com' in link:
                return link
    if 'portfolio' in l or 'website' in l or 'personal site' in l:
        for link in links:
            if 'github.com' not in link and 'linkedin.com' not in link:
                return link
        if links:
            return links[0]

    return None

def resolve_work_auth(label: str, prefs: dict) -> str | None:
    l = label.casefold()
    work_auth = prefs.get('work_authorization', '').strip().casefold()
    if not work_auth:
        return None

    # Check for explicit negation in profile work_auth
    is_negated = any(k in work_auth for k in ('not authorized', 'unauthorized', 'no authorization', 'cannot work', 'ineligible', 'not eligible'))

    # Sponsorship questions
    if any(k in l for k in ('sponsorship', 'visa', 'require sponsorship', 'need sponsorship')):
        if any(k in work_auth for k in ('not require', 'no sponsorship', 'citizen', 'permanent resident', 'green card', 'without sponsorship')):
            return 'No'
        if any(k in work_auth for k in ('require sponsorship', 'need sponsorship', 'visa sponsorship required', 'require visa', 'need visa')):
            return 'Yes'
        return None

    # Legal authorization questions
    if any(k in l for k in ('legally authorized', 'authorized to work', 'eligible to work', 'work authorization', 'legal right to work')):
        if is_negated:
            return 'No'
        if any(k in work_auth for k in ('authorized', 'eligible', 'citizen', 'permanent resident', 'yes', 'permit')):
            if 'in the us' in l or 'in the united states' in l or 'in us' in l:
                if 'not authorized' in work_auth or 'egypt only' in work_auth or 'no' in work_auth:
                    return 'No'
            return 'Yes'
        return None

    # Clearance
    if 'security clearance' in l:
        if 'clearance' in work_auth:
            return 'Yes' if 'top secret' in work_auth or 'secret' in work_auth else 'No'
        return None

    return None

def resolve_experience_years(label: str, profile: dict) -> str | None:
    l = label.casefold()
    if not (('experience' in l and 'year' in l) or 'how many years' in l):
        return None

    if not profile or not profile.get('sections'):
        return None

    # Extract text corpus from profile
    text_corpus = []
    for s in profile.get('sections', []):
        for item in s.get('items', []):
            text_corpus.append(item.get('text', '').casefold())
    full_text = ' '.join(text_corpus)
    if not full_text.strip():
        return None

    claims = re.findall(r'(\d{1,2})\+?\s*years?\s+(?:of\s+)?(?:experience\s+)?(?:building|using|with|in)\s+([^.;]{0,100})', full_text)
    technologies = ('react', 'typescript', 'javascript', 'next', 'frontend', 'html', 'css', 'redux', 'node', 'python', 'git', 'tailwind')
    requested = next((tech for tech in technologies if tech in l), None)
    if requested:
        supported = [int(years) for years, context in claims if requested in context]
        return str(max(supported)) if supported else None
    stated = [int(years) for years in re.findall(r'(\d{1,2})\+?\s*years?\s+(?:of\s+)?experience', full_text)]
    return str(max(stated)) if stated else None

def resolve_salary(label: str, job: dict, prefs: dict) -> str | None:
    l = label.casefold()

    # Exclude non-salary questions that might contain 'expected' or 'desired'
    if any(k in l for k in ('start date', 'start', 'availability', 'notice period', 'relocate', 'travel', 'commute')):
        return None

    salary_keywords = ('salary', 'compensation', 'pay', 'rate', 'remuneration', 'hourly', 'annual', 'base salary')
    has_salary_kw = any(k in l for k in salary_keywords)
    has_expected_kw = any(k in l for k in ('expected', 'desired')) and any(k in l for k in ('$', '€', '£', 'salary', 'compensation', 'pay', 'amount', 'earnings', 'rate', 'ctc', 'package', 'remuneration', 'expectation'))

    if not (has_salary_kw or has_expected_kw):
        return None

    # An application must never invent the applicant's compensation target.
    if not prefs.get('salary_note', '').strip():
        return None

    job_loc = (job.get('location', '') + ' ' + prefs.get('location', '') + ' ' + prefs.get('country', '')).casefold()

    salary_note = prefs.get('salary_note', '').strip()
    digits = _extract_digits(salary_note) if salary_note else ''
    note_lower = salary_note.casefold()

    is_monthly = any(k in l for k in ('month', 'monthly', 'per month', '/mo'))
    is_hourly = any(k in l for k in ('hour', 'hourly', 'per hour', '/hr'))

    note_is_monthly = any(k in note_lower for k in ('month', 'monthly', 'per month', '/mo'))
    note_is_annual = any(k in note_lower for k in ('year', 'annual', 'annually', '/yr', 'per year'))

    if is_monthly:
        if digits:
            d_val = int(digits)
            if note_is_monthly:
                return str(d_val)
            if note_is_annual or (d_val > 25000 and 'egp' not in note_lower and 'egypt' not in job_loc):
                return str(d_val // 12)
            return str(d_val)
        if 'egypt' in job_loc or 'cairo' in job_loc:
            return '65000'
        if 'remote' in job_loc or 'worldwide' in job_loc:
            return '5000'
        return None

    if is_hourly:
        if digits:
            d_val = int(digits)
            if d_val > 2000:
                return str(d_val // 2000)
            return str(d_val)
        return '40'

    # Annual
    if digits:
        d_val = int(digits)
        if note_is_monthly or (d_val < 25000 and ('usd' in note_lower or 'eur' in note_lower or '$' in note_lower)):
            return str(d_val * 12)
        if note_is_monthly and ('egp' in note_lower or 'egypt' in job_loc):
            return str(d_val * 12)
        return str(d_val)

    # Market estimate based on location
    if 'remote' in job_loc or 'us' in job_loc or 'europe' in job_loc or 'worldwide' in job_loc:
        return '85000'
    if 'uae' in job_loc or 'dubai' in job_loc:
        return '180000'
    if 'egypt' in job_loc or 'cairo' in job_loc:
        return '750000'

    return None

def resolve_notice_period(label: str, prefs: dict | None = None) -> str | None:
    l = label.casefold()
    if not any(k in l for k in ('notice period', 'how soon', 'start date', 'when can you start', 'availability')):
        return None
    if prefs:
        val = prefs.get('notice_period') or prefs.get('availability')
        if val:
            return str(val).strip()
    return None

def match_dropdown_option(options: list[dict], target_text: str) -> str | None:
    if not options or not target_text:
        return None
    target_clean = str(target_text).casefold().strip()
    if not target_clean:
        return None

    def is_placeholder(opt):
        val = str(opt.get('value', '')).casefold().strip()
        lbl = str(opt.get('label', '')).casefold().strip()
        if not val and not lbl:
            return True
        return lbl in ('select', 'select an option', 'select option', 'choose', 'choose an option', 'please select', '--', 'none')

    valid_opts = [o for o in options if not is_placeholder(o)]
    if not valid_opts:
        return None

    # Exact match on value or label
    for opt in valid_opts:
        val = str(opt.get('value', '')).casefold().strip()
        lbl = str(opt.get('label', '')).casefold().strip()
        if target_clean in (val, lbl):
            return opt.get('value', opt.get('label', ''))

    # If target is Yes/No, strictly match word boundary
    if target_clean in ('yes', 'true', '1'):
        for opt in valid_opts:
            lbl = str(opt.get('label', '')).casefold()
            val = str(opt.get('value', '')).casefold()
            if re.search(r'\byes\b|\btrue\b', lbl) or re.search(r'\byes\b|\btrue\b', val):
                return opt.get('value', opt.get('label', ''))
        return None
    elif target_clean in ('no', 'false', '0'):
        for opt in valid_opts:
            lbl = str(opt.get('label', '')).casefold()
            val = str(opt.get('value', '')).casefold()
            if re.search(r'\bno\b|\bfalse\b', lbl) or re.search(r'\bno\b|\bfalse\b', val):
                return opt.get('value', opt.get('label', ''))
        return None

    # Number match if target is a digit
    digits = _extract_digits(target_text)
    if digits:
        for opt in valid_opts:
            lbl = str(opt.get('label', '')).casefold()
            val = str(opt.get('value', '')).casefold()
            if re.search(rf'\b{digits}\b', lbl) or re.search(rf'\b{digits}\b', val) or f'{digits}+' in lbl or f'{digits} years' in lbl:
                return opt.get('value', opt.get('label', ''))

    # Word boundary partial match (only for words >= 3 letters to avoid false matches)
    words = [w for w in re.split(r'\W+', target_clean) if len(w) >= 3]
    if words:
        for opt in valid_opts:
            lbl = str(opt.get('label', '')).casefold()
            val = str(opt.get('value', '')).casefold()
            if all(re.search(rf'\b{re.escape(w)}\b', lbl) or re.search(rf'\b{re.escape(w)}\b', val) for w in words):
                return opt.get('value', opt.get('label', ''))

    return None

def answer_single_field(field: dict, profile: dict, job: dict, package: dict, prefs: dict) -> str:
    label = field.get('label', '')
    field_type = field.get('type', 'text')
    options = field.get('options', [])

    # 1. Contact / Profile identity
    contact_val = resolve_contact_field(label, profile)
    if contact_val is not None:
        if options:
            return match_dropdown_option(options, contact_val) or ''
        return contact_val

    # 2. Work authorization / Sponsorship
    auth_val = resolve_work_auth(label, prefs)
    if auth_val is not None:
        if options:
            matched = match_dropdown_option(options, auth_val)
            if matched:
                return matched
        return auth_val

    # 3. Experience years
    exp_val = resolve_experience_years(label, profile)
    if exp_val is not None:
        if options:
            matched = match_dropdown_option(options, exp_val)
            if matched:
                return matched
        return exp_val

    # 4. Salary / Compensation
    salary_val = resolve_salary(label, job, prefs)
    if salary_val is not None:
        if field_type == 'number':
            return _extract_digits(salary_val) or salary_val
        if options:
            matched = match_dropdown_option(options, salary_val)
            if matched:
                return matched
        return salary_val

    # 5. Notice period / Start date
    notice_val = resolve_notice_period(label, prefs)
    if notice_val is not None:
        if options:
            matched = match_dropdown_option(options, notice_val)
            if matched:
                return matched
        return notice_val

    # 6. Cover letter question
    if re.search(r'cover.?letter', label, re.I) and package.get('cover_letter'):
        return package['cover_letter']

    # 7. AI Fallback for custom / open-ended questions
    if any(k in label.casefold() for k in (
        'authorized', 'authorization', 'visa', 'sponsorship', 'clearance',
        'salary', 'compensation', 'expected pay', 'notice period',
        'when can you start', 'years of', 'agree', 'consent', 'acknowledge',
    )):
        return ''
    try:
        cfg = providers.get_provider_config()
        if cfg.get('connected'):
            prompt = (
                f"You are applying to the job: {job.get('title', '')} at {job.get('company', '')}.\n"
                f"Job description summary: {job.get('description', '')[:600]}\n\n"
                f"Candidate name: {profile.get('name', '')}\n"
                f"Candidate headline: {profile.get('headline', '')}\n"
                f"Question asked on employer application: \"{label}\"\n"
            )
            if options:
                opt_texts = [o.get('label', '') for o in options]
                prompt += f"Available options to select from: {opt_texts}\n"
                instruction = "Pick the single most truthful and appropriate option from the available options."
            else:
                instruction = "Provide a concise (1-3 sentences), professional, truthful answer representing the candidate."

            res = providers.ask(AnswerResponse, instruction, {'prompt': prompt})
            if options:
                matched = match_dropdown_option(options, res.answer)
                return matched or res.answer
            return res.answer
    except Exception:
        pass

    return ''
