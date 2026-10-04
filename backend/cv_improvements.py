"""Evidence-grounded edits for requirements that are missing from a job CV."""
import copy

from . import profile as profiles, providers, store, tailoring


MAX_SELECTIONS = 30


def _current_package(job_id, package_hash):
    job = store.get_job(job_id)
    if job['state'] in ('submitted', 'submitting', 'uncertain'):
        raise ValueError('Resolve this application status before changing its CV.')
    package = store.get_package(job_id)
    if not package:
        raise ValueError('Prepare a CV before improving requirement coverage.')
    if package['hash'] != package_hash:
        raise ValueError('The CV package changed. Reload coverage and draft changes again.')
    snapshot = package.get('job_snapshot') or {}
    if any(snapshot.get(key) != job.get(key) for key in ('title', 'company', 'location', 'url', 'description')):
        raise ValueError('Job details changed since this CV was prepared. Prepare a fresh CV before improving it.')
    master = store.setting('profile') or {}
    if package['profile_revision'] != master.get('revision'):
        raise ValueError('Your master profile changed. Prepare a fresh CV before improving it.')
    return job, package


def _section_for(profile, evidence_id):
    return next(
        (section['title'] for section in profile.get('sections', [])
         if any(item['id'] == evidence_id for item in section.get('items', []))),
        '',
    )


def _selection_data(package, selections):
    if not selections or len(selections) > MAX_SELECTIONS:
        raise ValueError(f'Select between 1 and {MAX_SELECTIONS} missing requirements at a time.')
    indexes = [selection['requirement_index'] for selection in selections]
    if len(indexes) != len(set(indexes)):
        raise ValueError('A requirement can only be selected once.')

    source = profiles.evidence(package['profile'])
    editable = tailoring.editable_profile_entries(package['profile'])
    source.update({key: package.get('source_evidence', {}).get(key, editable.get(key, value))
                   for key, value in editable.items()})
    requirements = []
    user_evidence = {}
    normalized_selections = []
    rows = package['requirements']
    for selection in selections:
        index = selection['requirement_index']
        if index >= len(rows):
            raise ValueError('A selected requirement is no longer in this package. Reload coverage.')
        requirement = rows[index]
        if requirement['support'] != 'missing':
            raise ValueError('Only requirements currently marked missing can be improved here.')

        evidence_text = (selection.get('evidence_text') or '').strip()
        evidence_ids = [item_id for item_id in requirement.get('evidence_ids', []) if item_id in source]
        confirmed = bool(selection.get('evidence_confirmed'))
        if evidence_text and (len(evidence_text) < 12 or not confirmed):
            raise ValueError('Confirm that the experience you supplied is accurate before drafting.')
        if not evidence_ids and not evidence_text:
            raise ValueError('Add truthful experience evidence for every selected requirement with no CV evidence.')

        user_id = None
        if evidence_text:
            user_id = f'user:{index}'
            source[user_id] = evidence_text
            user_evidence[user_id] = evidence_text
        requirements.append({
            'index': index,
            'text': requirement['text'],
            'priority': requirement['priority'],
            'source_quote': requirement['source_quote'],
            'existing_evidence_ids': evidence_ids,
            'user_evidence_id': user_id,
        })
        normalized_selections.append({
            'requirement_index': index,
            'evidence_text': evidence_text,
            'evidence_confirmed': confirmed,
        })
    return source, editable, requirements, user_evidence, normalized_selections


def draft(job_id, package_hash, selections):
    job, package = _current_package(job_id, package_hash)
    source, editable, requirements, user_evidence, normalized_selections = _selection_data(package, selections)
    editable_context = {
        evidence_id: {
            'current_text': next(
                item['text'] for section in package['profile']['sections']
                for item in section['items'] if item['id'] == evidence_id
            ),
            'original_evidence': source[evidence_id],
            'section': _section_for(package['profile'], evidence_id),
        }
        for evidence_id in editable
    }

    proposed = providers.ask(
        providers.CVImprovements,
        'For the selected missing job requirements, propose concise, truthful CV improvements. '
        'Use only the supplied original CV evidence or the user-confirmed evidence attached to that same requirement. '
        'For action="rewrite", choose an editable evidence_id and preserve its facts, scope, dates, ownership, seniority, qualifications, technologies and quantities. '
        'For action="add", choose only that requirement’s user evidence_id and add a concise bullet to the Summary section; never create an employer, role, date, metric, skill, credential or achievement. '
        'Do not add keyword-only claims. A proposed change may address multiple requirement indices only when the same wording is directly supported by its evidence. '
        'Omit a requirement if no truthful improvement is possible. Return only changes that can be supported by the supplied evidence.',
        {
            'job_title': job['title'],
            'selected_requirements': requirements,
            'editable_entries': editable_context,
            'cv_source_evidence': {key: value for key, value in source.items() if not key.startswith('user:')},
            'user_confirmed_evidence': user_evidence,
        },
    )

    allowed_indexes = {row['index'] for row in requirements}
    claimed_indexes = set()
    used_sources = set()
    candidates = []
    for change in proposed.changes:
        indexes = list(dict.fromkeys(change.requirement_indices))
        if not indexes or any(index not in allowed_indexes or index in claimed_indexes for index in indexes):
            continue
        if len(change.text.strip()) > 1000 or not change.text.strip():
            continue
        if change.action == 'rewrite':
            if change.evidence_id not in editable or change.evidence_id in used_sources:
                continue
            original = source[change.evidence_id]
            before = editable[change.evidence_id]
            if not tailoring.guard_rewrite(original, change.text):
                continue
            section = _section_for(package['profile'], change.evidence_id)
            if not section:
                continue
            evidence_text = original
        else:
            # New factual statements are permitted only from explicitly confirmed user evidence.
            if len(indexes) != 1 or change.evidence_id not in user_evidence:
                continue
            if indexes[0] != int(change.evidence_id.split(':', 1)[1]):
                continue
            original = user_evidence[change.evidence_id]
            if not tailoring.guard_rewrite(original, change.text):
                continue
            before = ''
            section = 'Summary'
            evidence_text = original

        used_sources.add(change.evidence_id)
        claimed_indexes.update(indexes)
        candidates.append({
            'id': store.uid(),
            'action': change.action,
            'requirement_indices': indexes,
            'evidence_id': change.evidence_id,
            'section': section,
            'before': before,
            'after': change.text.strip(),
            'source_evidence': evidence_text,
            'evidence_confirmed': change.evidence_id in user_evidence,
        })

    if candidates:
        audit = providers.ask(
            providers.Checks,
            'Audit every proposed CV change against its exact original evidence. supported=true only if every factual claim in the rewrite is entailed by that evidence. '
            'Reject unsupported technologies, quantities, qualifications, years, seniority, scope, ownership and achievements. Treat user-confirmed evidence as an assertion by the applicant, but do not add anything beyond it. Be conservative.',
            {'entries': [
                {'evidence_id': item['id'], 'original': item['source_evidence'], 'rewrite': item['after']}
                for item in candidates
            ]},
        ).checks
        allowed = {check.evidence_id for check in audit if check.supported}
        candidates = [item for item in candidates if item['id'] in allowed]

    unresolved = [
        {'requirement_index': row['index'], 'text': row['text']}
        for row in requirements
        if not any(row['index'] in item['requirement_indices'] for item in candidates)
    ]
    draft_data = {
        'package_id': package['id'],
        'profile_revision': package['profile_revision'],
        'selections': normalized_selections,
        'suggestions': candidates,
        'unresolved': unresolved,
    }
    return draft_data


def _apply_suggestions(profile, suggestions):
    updated = copy.deepcopy(profile)
    changes = []
    added_evidence = {}
    for suggestion in suggestions:
        if suggestion['action'] == 'rewrite':
            matched = next((
                item for section in updated['sections'] for item in section['items']
                if item['id'] == suggestion['evidence_id']
            ), None)
            if not matched or matched['text'] != suggestion['before']:
                raise ValueError('The source CV statement changed. Draft improvements again.')
            if not tailoring.guard_rewrite(suggestion['source_evidence'], suggestion['after']):
                raise ValueError('A proposed change alters a number from its source evidence.')
            matched['text'] = suggestion['after']
            changes.append({
                'id': matched['id'], 'before': suggestion['before'], 'after': suggestion['after'],
                'evidence': suggestion['source_evidence'],
            })
        else:
            if suggestion['section'] != 'Summary' or not suggestion.get('evidence_confirmed'):
                raise ValueError('New CV statements require confirmed applicant evidence and a Summary placement.')
            if not tailoring.guard_rewrite(suggestion['source_evidence'], suggestion['after']):
                raise ValueError('A proposed change alters a number from its source evidence.')
            summary = next((section for section in updated['sections'] if section['title'] == 'Summary'), None)
            if not summary:
                summary = {'title': 'Summary', 'items': []}
                updated['sections'].insert(0, summary)
            item_id = store.uid()
            summary['items'].append({'id': item_id, 'text': suggestion['after']})
            added_evidence[item_id] = suggestion['source_evidence']
            changes.append({
                'id': item_id, 'before': '', 'after': suggestion['after'],
                'evidence': suggestion['source_evidence'],
            })
    return updated, changes, added_evidence


def apply(job_id, package_hash, draft_id, suggestion_ids):
    if not suggestion_ids or len(suggestion_ids) > MAX_SELECTIONS:
        raise ValueError('Choose at least one verified edit to apply.')
    job, package = _current_package(job_id, package_hash)
    draft_data = store.claim_cv_improvement_draft(draft_id, job_id, package_hash)
    try:
        if draft_data.get('package_id') != package['id'] or draft_data.get('profile_revision') != package['profile_revision']:
            raise ValueError('The CV package changed. Draft improvements again.')
        suggestions_by_id = {item['id']: item for item in draft_data.get('suggestions', [])}
        if len(suggestion_ids) != len(set(suggestion_ids)) or any(key not in suggestions_by_id for key in suggestion_ids):
            raise ValueError('One or more selected AI edits are no longer available. Draft improvements again.')
        chosen = [suggestions_by_id[key] for key in suggestion_ids]

        updated_profile, changes, added_evidence = _apply_suggestions(package['profile'], chosen)
        data = store.package_data(package)
        data['profile'] = updated_profile
        data['source_evidence'] = {**(data.get('source_evidence') or {}), **added_evidence}
        data['changes'] = [*data.get('changes', []), *changes]
        reqs = [
            {'text': row['text'], 'priority': row['priority'], 'source_quote': row['source_quote']}
            for row in data['requirements']
        ]
        data['requirements'] = tailoring.coverage(reqs, updated_profile, ai=True)
        data['score'] = tailoring.score(data['requirements'])
        data['cv_reviewed'] = False
        data['coverage_reviewed'] = False
        data['mode'] = 'ai'
        data['note'] = 'AI-audited CV improvements applied. Review every updated statement and reassessed requirement before approval.'

        package_id = store.uid()
        from .documents import generate, verify_files
        data['files'] = {**data.get('files', {}), **generate(updated_profile, package_id)}
        candidate = {**data, 'id': package_id}
        verify_files(candidate)
        store.save_package(job_id, data, package_id=package_id)
        store.update_job(job_id, state='awaiting_review', score=data['score'])
        store.event(job_id, f'Applied {len(changes)} AI-audited CV improvements. Review the new package before approval.')
        store.finish_cv_improvement_draft(draft_id, 'used')
        return {'package_id': package_id, 'score': data['score'], 'change_count': len(changes)}
    except Exception:
        store.finish_cv_improvement_draft(draft_id, 'failed')
        raise
