"""Deterministic reader summary of saved evidence, shared by UI and export."""
def decision_summary(row):
    report = row.get('report') or {}
    evidence = report.get('evidence', [])
    findings = [e for e in evidence if e.get('score') is not None and e['score'] >= .5
                and e.get('metadata', {}).get('risk_eligible') is not False
                and e.get('category') not in {'synthetic_media', 'manipulation', 'provenance'}
                and e.get('source') not in {'image_detector', 'video_detector', 'audio_detector', 'url_detector'}]
    scenarios = report.get('scenarios', [])
    gaps = list(dict.fromkeys([e.get('explanation', 'Check unavailable') for e in evidence
           if e.get('label') in {'unavailable', 'verification_unavailable'}] +
           [c.get('summary', c.get('title', 'Check incomplete')) for c in report.get('checks', [])
            if c.get('status') in {'unavailable', 'partial', 'not_checked'}]))
    title = 'Review the observed security indicators' if findings or scenarios else 'No suspicious indicator identified in completed checks'
    if not evidence: title = 'No completed evidence available'
    elif not findings and not scenarios and (gaps or report.get('risk_score') is None): title = 'Limited evidence; security remains unresolved'
    actions = list(dict.fromkeys(a for s in scenarios for a in s.get('recommendations', [])))
    if row.get('input_type') == 'url':
        from app.services.url_summary import summarize_url
        url = summarize_url(row['name'], report)
        title = url['title']; actions.extend(url['actions'])
    if report.get('conflicts'): actions.insert(0, 'Resolve conflicting findings before relying on this assessment.')
    if not actions: actions = ['Verify the sender or creator through an independently obtained official channel before paying or sharing sensitive information.']
    return dict(title=title, meaning='Findings describe observed evidence, not proof of fraud. AI origin is assessed separately from cybersecurity risk.',
                findings=[dict(id=e['id'], label=e['label'].replace('_', ' '), explanation=e['explanation']) for e in findings],
                scenarios=[dict(label=s['label'], explanation=s['explanation'], evidence_ids=s.get('evidence_ids', [])) for s in scenarios],
                actions=list(dict.fromkeys(actions)), gaps=gaps,
                evidence_count=len(evidence), conflict_count=len(report.get('conflicts', [])))
