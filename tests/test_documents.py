from docx import Document

from backend import documents


def test_experience_role_titles_are_emphasized_and_stay_with_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(documents.store, 'DATA', tmp_path)
    profile = {
        'name': 'Candidate Name',
        'headline': 'Frontend Engineer',
        'sections': [{
            'title': 'Professional Experience',
            'items': [
                {'id': 'role', 'text': 'Front-End Developer - Freelance, Cairo'},
                {'id': 'dates', 'text': '01/2022 - Present (part-time / contract)'},
                {'id': 'detail', 'text': 'Built responsive web applications for clients.'},
            ],
        }],
    }

    files = documents.generate(profile, 'role-title-formatting')
    generated_doc = Document(tmp_path / 'documents' / 'role-title-formatting' / 'cv.docx')
    paragraphs = {paragraph.text: paragraph for paragraph in generated_doc.paragraphs}
    role = paragraphs['Front-End Developer - Freelance, Cairo']
    dates = paragraphs['01/2022 - Present (part-time / contract)']

    assert files['pdf']['path'].endswith('cv.pdf')
    assert role.runs[0].bold is True
    assert role.runs[0].font.size.pt == 10.5
    assert role.paragraph_format.keep_with_next is True
    assert dates.runs[0].bold is True
    assert dates.paragraph_format.keep_with_next is True
