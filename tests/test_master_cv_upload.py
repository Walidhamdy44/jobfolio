from io import BytesIO

from reportlab.pdfgen import canvas

from backend import store


def sample_cv_pdf():
    output = BytesIO()
    pdf = canvas.Canvas(output)
    lines = [
        'Upload Candidate',
        'Frontend Engineer',
        'Cairo, Egypt | upload@example.com | +201010101010',
        'https://example.com | https://github.com/upload',
        'SUMMARY',
        'Frontend engineer with six years of experience building web applications.',
        'PROFESSIONAL EXPERIENCE',
        'Frontend Engineer at Example Studio 2020-2024',
        'Built React interfaces with TypeScript.',
        'TECHNICAL SKILLS',
        'React, TypeScript, CSS',
    ]
    y = 800
    for line in lines:
        pdf.drawString(48, y, line)
        y -= 24
    pdf.save()
    return output.getvalue()


def test_upload_parses_locally_then_saves_as_master_profile(client):
    original_profile = store.setting('profile')
    original_bytes = sample_cv_pdf()
    response = client.post(
        '/api/profile/master-cv',
        content=original_bytes,
        headers={'Content-Type': 'application/pdf'},
    )

    assert response.status_code == 200, response.text
    candidate = response.json()['profile']
    assert candidate['name'] == 'Upload Candidate'
    assert candidate['source_file'].startswith('master_cv_')
    assert store.setting('profile') == original_profile
    assert (store.DATA / candidate['source_file']).read_bytes() == original_bytes

    body = {key: value for key, value in candidate.items() if key != 'revision'}
    saved = client.put('/api/profile', json=body)
    assert saved.status_code == 200, saved.text
    active_profile = store.setting('profile')
    assert active_profile['source_file'] == candidate['source_file']
    assert active_profile['revision'] == original_profile['revision'] + 1
    downloaded = client.get('/api/master-cv')
    assert downloaded.status_code == 200
    assert downloaded.content == original_bytes


def test_upload_rejects_non_pdf_without_changing_master_profile(client):
    original_profile = store.setting('profile')
    response = client.post(
        '/api/profile/master-cv',
        content=b'not a PDF',
        headers={'Content-Type': 'application/pdf'},
    )

    assert response.status_code == 400
    assert 'not a valid PDF' in response.json()['detail']
    assert store.setting('profile') == original_profile
