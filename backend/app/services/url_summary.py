"""Evidence-derived URL narrative shared by the UI and PDF; no invented verdicts."""
from urllib.parse import urlsplit


def summarize_url(name, report):
    evidence=report.get('evidence',[])
    assets=report.get('assets',[])
    graph=report.get('graph',{})
    root=next((a for a in assets if a.get('type')=='url' and a.get('url')==name),None)
    if not root:
        root=next((n for n in graph.get('nodes',[]) if n.get('type')=='url' and n.get('label')==name),None)
    root_id=root.get('id') if root else None
    chain=next((e.get('metadata',{}).get('chain',[]) for e in evidence if e.get('asset_id')==root_id and e.get('label')=='redirect_chain'),[])
    final=chain[-1][1] if chain else name
    ids={root_id} if root_id else set()
    for _ in range(6):
        ids.update(e['target'] for e in graph.get('edges',[]) if e.get('relation')=='redirects_to' and e['source'] in ids)
    pages={e['target'] for e in graph.get('edges',[]) if e.get('relation')=='contains' and e['source'] in ids}
    page=next((e for e in evidence if e.get('label')=='page_metadata' and e.get('asset_id') in pages),None)
    forms=(page or {}).get('metadata',{}).get('data_collection',{}).get('forms',[])
    browser=next((e for e in evidence if e.get('label')=='browser_observation' and e.get('asset_id') in pages),None)
    if browser:
        forms=browser.get('metadata',{}).get('rendered_collection',{}).get('forms',forms)
    fields=sorted({kind for form in forms for kind in form.get('displayed_field_types',form.get('field_types',[]))})
    flags=[e for e in evidence if e.get('score') is not None and e['score']>=.5 and e.get('metadata',{}).get('risk_eligible') is not False and e.get('source') not in {'url_detector','image_detector','audio_detector','video_detector'} and e.get('category') not in {'synthetic_media','manipulation','provenance'}]
    missing=[]
    for e in evidence:
        if e.get('label') in {'unavailable','verification_unavailable'} and e.get('explanation') not in missing:missing.append(e['explanation'])
    checks=report.get('checks',[])
    for c in checks:
        if c.get('status')=='not_checked' and c.get('summary') not in missing:missing.append(c['summary'])
    observations=[]
    if page:
        observations.append('Fetched and inspected the public page HTML.')
        if browser:observations.append('Also inspected the rendered page and initial requests in a restricted, unauthenticated browser session.')
        observations.append(f'{len(forms)} declared form destination(s); visible questions concern: '+(', '.join(fields) if fields else 'field types not established from observed markup')+'.')
        if any(field.get('disabled') for form in forms for field in form.get('fields',[])):observations.append('Some question controls were disabled in the observed page. Their labels are recorded, but submission behavior was not established.')
    if chain:observations.append(f'Followed {len(chain)} redirect(s) for the submitted URL; final host: {urlsplit(final).hostname}.')
    else:observations.append('No redirect recorded for the submitted URL.' if page else 'No completed page or redirect inspection.')
    actions=[]
    if set(fields)&{'password','authentication secret','payment card'}:actions.append('Do not submit account secrets or card details until you independently verify why they are required and who receives them.')
    if forms:actions.append('Confirm the form owner through the organization’s independently obtained official channel before sharing personal information.')
    if any(c.get('id')=='malware' and c.get('status') in {'unavailable','partial','not_checked'} for c in checks):actions.append('The malware check is incomplete; avoid opening downloaded files until a working scanner checks them.')
    if not page:actions.append('Retry when page access is available, or provide the public viewing URL if this link requires sign-in.')
    if not actions:actions.append('Verify the source independently before relying on this page for consequential actions.')
    return {'schema':1,'title':'Security indicators need review' if flags else 'Page inspected; no high-risk indicator identified' if page else 'Page inspection unavailable',
            'meaning':'These are observed screening results, not verification of the operator or a safety certificate. '+('Browser observation covers initial loading only; later interactions and authenticated content were not tested.' if browser else 'Scripts, later interactions and authenticated content were not observed.'),
            'page_title':(page or {}).get('metadata',{}).get('title',''),'final_host':urlsplit(final).hostname,
            'observations':observations,'requested_data':fields,'findings':[{'id':e['id'],'label':e['label'],'explanation':e['explanation']} for e in flags],
            'gaps':missing,'actions':actions,'page_inspected':bool(page)}
