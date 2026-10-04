from pathlib import Path

from backend import profile, providers, store


def test_ai_structure_falls_back_when_provider_drops_source_sections(monkeypatch):
    source_text = """Walid Hamdy
Frontend Engineer
Cairo | walid@example.com | +20 100 000 0000
github.com/walid
SUMMARY
Frontend engineer building accessible web applications.
TECHNICAL SKILLS
Languages: JavaScript, TypeScript
PROFESSIONAL EXPERIENCE
Front-End Developer - Example Company
• Built responsive React applications.
SELECTED PROJECTS
Example Platform
• Built a Next.js platform.
EDUCATION AND CERTIFICATIONS
Bachelor of Science in Computer Science
LANGUAGES
Arabic: Native | English: Advanced
"""
    truncated = providers.StructuredProfile(
        name='Walid Hamdy',
        headline='Frontend Engineer',
        email='walid@example.com',
        phone='+20 100 000 0000',
        location='Cairo',
        links=['github.com/walid'],
        sections=[
            providers.StructuredSection(title='Summary', items=['Frontend engineer.']),
            providers.StructuredSection(title='Technical Skills', items=['JavaScript, TypeScript']),
            providers.StructuredSection(title='Professional Experience', items=['Front-End Developer']),
        ],
    )

    monkeypatch.setattr(
        profile,
        'get_master_pdf_text_for',
        lambda source_file=None: (source_text, Path('resume.pdf')),
    )
    monkeypatch.setattr(
        store,
        'setting',
        lambda key, default=None: {'source_file': 'resume.pdf', 'revision': 4} if key == 'profile' else default,
    )
    monkeypatch.setattr(
        providers,
        'get_provider_config',
        lambda: {'connected': True, 'provider': 'openrouter'},
    )
    monkeypatch.setattr(providers, 'ask', lambda *args, **kwargs: truncated)

    result = profile.structure_cv(mode='ai', source_file='resume.pdf')

    assert [section['title'] for section in result['sections']] == [
        heading.title() for heading in profile.HEADINGS
    ]
