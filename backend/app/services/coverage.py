"""Describe completed capabilities from actual evidence, never registry availability alone."""
def investigation_checks(assets, evidence):
    kinds = {a.get('type') for a in assets}
    checks = []
    missing_labels = {'unavailable', 'verification_unavailable'}
    def add(key, title, items, limitation, success='Check completed'):
        completed = [e for e in items if e.label not in missing_labels]
        missing = [e for e in items if e.label in missing_labels]
        flags = [e for e in completed if e.score is not None and e.score >= .5 and e.category not in {'synthetic_media', 'manipulation'} and e.metadata.get('risk_eligible') is not False]
        status = 'findings' if flags else 'partial' if completed and missing else 'unavailable' if missing else 'completed' if completed else 'not_checked'
        checks.append(dict(id=key, title=title, status=status, summary=f'{len(flags)} finding(s) need review' if flags else success if completed else 'Check could not complete' if missing else 'No result available for this check', evidence_ids=[e.id for e in items], limitations=limitation, unavailable_reasons=list(dict.fromkeys(e.explanation for e in missing))))
    if any(e.source == 'document_inspector' for e in evidence):
        add('document','Document text & active content',[e for e in evidence if e.source == 'document_inspector'],'Bounded structural inspection. Document claims, authorship and signature authenticity are not verified. Macros and scripts are never executed.','Document text, links and active-content markers inspected')
    if 'url' in kinds or 'webpage' in kinds:
        from app.core.config import settings
        if settings.enable_browser_inspection:
            add('browser', 'Rendered page & initial requests', [e for e in evidence if e.source == 'browser_inspector'], 'Restricted initial-load observation, no form submissions or authenticated interactions. Blocked resources can alter page behavior.')
        add('phishing', 'Phishing & impersonation', [e for e in evidence if e.source in {'webpage','safe_fetch'} and (e.category in {'phishing','identity_mismatch','social_engineering'} or e.label in missing_labels or e.label == 'page_metadata')], 'Static page inspection. A blocked fetch prevents content analysis; third-party login services and brand mentions can be legitimate.')
        add('collection', 'Sensitive-data collection', [e for e in evidence if e.category == 'data_collection' or e.label == 'credential_destination_mismatch'], 'Declared fields, form destinations and inline API references only. No form submission, script execution or live data-flow monitoring.', 'Declared collection surfaces inspected')
        add('reputation', 'Malicious-link reputation', [e for e in evidence if e.source == 'reputation'], 'External reputation requires explicit configuration. No database match does not prove a URL is safe.')
        if checks[-1]['status'] == 'not_checked':
            from app.core.config import settings
            if settings.privacy_mode:
                checks[-1]['summary'] = 'External reputation queries are disabled by privacy mode'
            elif not settings.enable_external_reputation:
                checks[-1]['summary'] = 'External reputation service is not enabled'
    if kinds & {'file','image','video','audio','webpage','url'}:
        add('malware', 'Malware signatures', [e for e in evidence if e.source == 'clamav'], 'Only files actually downloaded or uploaded are scanned. A working local scanner and signatures are required; undetected threats remain possible.', 'Signature scan completed; inspect individual results')
        add('file', 'File structure & disguised content', [e for e in evidence if e.source == 'file_inspector'], 'File type, hash and bounded archive inspection. Executable content or a mismatched extension alone is not proof of malware.')
    for kind, title in [('image','AI-generated image'), ('video','Visual deepfake'), ('audio','Synthetic voice')]:
        if kind in kinds or (kind == 'audio' and 'video' in kinds):
            items = [e for e in evidence if e.source == kind + '_detector']
            add(kind, title, items, 'Model-specific screening, not forensic proof. Missing checkpoints mean this capability has not run.', 'Model inference completed; review its score and uncertainty')
    if kinds & {'image','video','audio'}:
        add('provenance', 'Content provenance', [e for e in evidence if e.source == 'c2pa'], 'Missing credentials are neutral. Valid credentials describe signed claims, not the truth of a scene.')
    return checks
