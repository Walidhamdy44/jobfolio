import re
from pypdf import PdfReader
from . import store

HEADINGS = ['SUMMARY', 'TECHNICAL SKILLS', 'PROFESSIONAL EXPERIENCE', 'SELECTED PROJECTS', 'EDUCATION AND CERTIFICATIONS', 'LANGUAGES']

def import_master():
    if store.setting('profile'):
        return
    sources = sorted(store.ROOT.glob('*.pdf'))
    if not sources:
        return
    source = next((p for p in sources if 'Walid_Hamdy' in p.name), sources[0])
    text = '\n'.join(p.extract_text() or '' for p in PdfReader(source).pages)
    text = re.sub(r'^Page \d+\s*$', '', text, flags=re.M)
    text = text.replace('PROFESSIONAL EXPERIENCE - CONTINUED', '').replace('\ufffd', '•')
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    sections, current = [], None
    for line in lines[4:]:
        if line in HEADINGS:
            current = {'title': line.title(), 'items': []}
            sections.append(current)
        elif current:
            items = current['items']
            start = (not items or line.startswith('•') or current['title'] == 'Technical Skills'
                     or bool(re.match(r'(Front-End|Front-end|Bachelor|Boutiqaat E-commerce|Skyloov Property|Learning Management|Arabic:)', line)))
            if start:
                items.append({'id': 'e' + str(sum(len(s['items']) for s in sections) + 1), 'text': line.lstrip('• ').strip()})
            else:
                items[-1]['text'] += ' ' + line
    contact = lines[2]
    email = re.search(r'[\w.+-]+@[\w.-]+', contact)
    phone = re.search(r'\+\d[\d ]+', contact)
    links = [x.strip() for x in lines[3].split('|')]
    profile = {'name': lines[0].title(), 'headline': lines[1], 'email': email[0] if email else '',
               'phone': phone[0].strip() if phone else '', 'location': contact.split('|')[0].strip(),
               'links': links, 'sections': sections, 'source_file': source.name, 'revision': 1}
    store.set_setting('profile', profile)
    store.set_setting('preferences', {'titles': ['Frontend Software Engineer', 'Frontend Developer', 'React Developer', 'Next.js Developer'],
        'location': '', 'remote_only': False, 'excluded_companies': [], 'excluded_keywords': [], 'salary_note': '', 'work_authorization': '', 'confirmed': False})

def get_master_pdf_text():
    sources = sorted(store.ROOT.glob('*.pdf'))
    if not sources:
        return '', None
    source = next((p for p in sources if 'Walid_Hamdy' in p.name), sources[0])
    text = '\n'.join(p.extract_text() or '' for p in PdfReader(source).pages)
    text = re.sub(r'^Page \d+\s*$', '', text, flags=re.M)
    text = text.replace('PROFESSIONAL EXPERIENCE - CONTINUED', '').replace('\ufffd', '•')
    return text.strip(), source

def structure_cv(mode='ai'):
    from . import providers
    text, source = get_master_pdf_text()
    if not text:
        raise ValueError('No master CV document found in your workspace to review.')

    current = store.setting('profile', {})
    source_file = current.get('source_file', source.name if source else '')
    revision = current.get('revision', 1)

    if mode == 'ai':
        cfg = providers.get_provider_config()
        if not cfg['connected']:
            p_name = providers.PROVIDER_DISPLAY_NAMES.get(cfg['provider'], cfg['provider'].capitalize())
            raise ValueError(f'Connect an API key for {p_name} in Connections first to review your CV with AI, or use local cleanup.')

        instruction = (
            "Parse and structure the provided resume/CV text into clean, professional, and coherent sections and entries. "
            "Do NOT split sentences or bullet points across multiple entries; merge lines into complete, grammatically sound statements. "
            "Retain all facts, dates, technologies, metrics, and achievements accurately with zero hallucination. "
            "Standardize section titles to: Summary, Technical Skills, Professional Experience, Selected Projects, Education and Certifications, Languages."
        )
        structured = providers.ask(providers.StructuredProfile, instruction, {"cv_text": text})

        sections = []
        counter = 1
        for s in structured.sections:
            sec_items = []
            for itm in s.items:
                clean_item = itm.strip()
                if clean_item:
                    sec_items.append({'id': f'e{counter}', 'text': clean_item})
                    counter += 1
            if sec_items:
                sections.append({'title': s.title.strip(), 'items': sec_items})

        return {
            'name': structured.name.strip().title(),
            'headline': structured.headline.strip(),
            'email': structured.email.strip(),
            'phone': structured.phone.strip(),
            'location': structured.location.strip(),
            'links': [l.strip() for l in structured.links if l.strip()],
            'sections': sections,
            'source_file': source_file,
            'revision': revision
        }
    else:
        # High quality local structure that merges fragmented lines into complete entries
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        sections, current_sec = [], None
        for line in lines[4:]:
            if line in HEADINGS:
                current_sec = {'title': line.title(), 'items': []}
                sections.append(current_sec)
            elif current_sec:
                items = current_sec['items']
                is_bullet = line.startswith('•') or line.startswith('-') or line.startswith('*')
                is_role_or_project = bool(re.search(r'\d{2}/\d{4}|Front-End|Bachelor|Project|Platform|System|Languages:|Frameworks:|Frontend Architecture:', line))
                if not items or is_bullet or is_role_or_project or current_sec['title'] == 'Technical Skills':
                    items.append({'id': f'e{sum(len(s["items"]) for s in sections) + 1}', 'text': line.lstrip('•-* ').strip()})
                else:
                    items[-1]['text'] += ' ' + line

        contact = lines[2] if len(lines) > 2 else ''
        email = re.search(r'[\w.+-]+@[\w.-]+', contact)
        phone = re.search(r'\+\d[\d ]+', contact)
        links = [x.strip() for x in lines[3].split('|')] if len(lines) > 3 else []
        return {
            'name': lines[0].title() if lines else 'Walid Hamdy',
            'headline': lines[1] if len(lines) > 1 else '',
            'email': email[0] if email else '',
            'phone': phone[0].strip() if phone else '',
            'location': contact.split('|')[0].strip() if contact else '',
            'links': links,
            'sections': sections,
            'source_file': source_file,
            'revision': revision
        }

def evidence(profile):
    return {i['id']: i['text'] for s in profile['sections'] for i in s['items']}

def cv_text(profile):
    return '\n'.join([profile['name'], profile['headline'], profile['email'], profile['phone'], profile['location'], *profile['links'],
        *[s['title'] + '\n' + '\n'.join(i['text'] for i in s['items']) for s in profile['sections']]])
