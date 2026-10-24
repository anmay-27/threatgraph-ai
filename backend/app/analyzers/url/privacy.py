"""Bounded static collection-surface inspection. Never submits forms or runs scripts."""
import re
from urllib.parse import urljoin, urlsplit
from app.analyzers.url.features import domain
from app.schemas.evidence import finding


def describe_field(field, soup):
    """Read accessible question labels; never capture submitted values."""
    parts = [str(field.get(key, '')) for key in ('name', 'id', 'autocomplete', 'aria-label', 'placeholder')]
    if field.get('id'):
        label = soup.find('label', attrs={'for': field['id']})
        if label: parts.append(label.get_text(' ',strip=True)[:300])
    for identifier in str(field.get('aria-labelledby','')).split()[:8]:
        label=soup.find(id=identifier)
        if label: parts.append(label.get_text(' ',strip=True)[:300])
    wrapper=field.find_parent('label')
    if wrapper: parts.append(wrapper.get_text(' ',strip=True)[:300])
    question=field.find_parent(attrs={'role':'listitem'})
    if question:
        heading=question.find(attrs={'role':'heading'})
        if heading: parts.append(heading.get_text(' ',strip=True)[:300])
    hint=' '.join(parts).lower()
    field_type=str(field.get('type','')).lower()
    kinds=set()
    patterns={
        'email': r'\be[ -]?mail\b',
        'phone': r'\b(phone|telephone|mobile|contact number|whatsapp)\b',
        'name': r'\b(full name|first name|last name|your name|student name)\b',
        'address': r'\b(home address|residential address|postal address|street address)\b',
        'date of birth': r'\b(date of birth|dob|birth date)\b',
        'payment card': r'cc-number|cc-csc|card.?number|\bcvv\b|\bcvc\b',
        'identity identifier': r'\b(ssn|aadhaar|aadhar|passport|national.?id)\b',
        'student identifier': r'\b(roll number|roll no|enrollment|enrolment|student id)\b',
        'authentication secret': r'one-time-code|\b(otp|recovery.?code|seed.?phrase|private key)\b',
        'password': r'\b(password|passcode)\b',
    }
    for kind,pattern in patterns.items():
        if re.search(pattern,hint): kinds.add(kind)
    if field_type=='password': kinds.add('password')
    if field_type=='email': kinds.add('email')
    if field_type=='tel': kinds.add('phone')
    return kinds, {'label': ' '.join(p for p in parts[3:] if p).strip()[:300], 'field_types': sorted(kinds), 'required': field.has_attr('required') or field.get('aria-required')=='true'}


def inspect_collection(soup, url, asset):
    base_tag = soup.find('base', href=True)
    base = urljoin(url, base_tag['href']) if base_tag else url
    findings, forms = [], []
    for index, form in enumerate(soup.find_all('form')[:50]):
        fields = list(form.select('input, textarea, select, [role="textbox"], [role="radiogroup"], [role="listbox"]'))
        if form.get('id'):
            fields += [f for f in soup.select('input[form],textarea[form],select[form]') if f.get('form') == form['id']]
        kinds = set()
        displayed_kinds = set()
        inventory=[]
        for field in fields[:200]:
            if field.get('type','').lower() in {'hidden','submit','button','reset'} or (field.get('form') and field.get('form') != form.get('id')):
                continue
            detected,description=describe_field(field,soup)
            description['disabled'] = field.has_attr('disabled') or field.get('aria-disabled') == 'true'
            displayed_kinds.update(detected)
            if description not in inventory: inventory.append(description)
            if not description['disabled']: kinds.update(detected)
        action = form.get('action', '').strip()
        destination = urljoin(base, action) if action else url
        targets = [(destination, form.get('method', 'get').lower())]
        buttons = list(form.select('[formaction]'))
        if form.get('id'):
            buttons += [b for b in soup.select('button[form][formaction],input[form][formaction]') if b.get('form') == form['id']]
        for button in buttons[:10]:
            if button.has_attr('disabled') or (button.get('form') and button.get('form') != form.get('id')):
                continue
            target_action = button['formaction'].strip()
            targets.append((urljoin(base, target_action) if target_action else url, button.get('formmethod', form.get('method', 'get')).lower()))
        for destination, method in dict.fromkeys(targets):
            if method == 'dialog':
                continue  # Closes a dialog; does not submit data.
            if method not in {'get', 'post'}:
                method = 'get'  # HTML's invalid-value default.
            scheme = urlsplit(destination).scheme.lower()
            external = scheme in {'http', 'https'} and domain(destination) != domain(url)
            secrets = bool(kinds & {'password', 'payment card', 'identity identifier', 'authentication secret'})
            info = dict(form_index=index, field_types=sorted(kinds), displayed_field_types=sorted(displayed_kinds), fields=inventory, destination=destination[:2000], method=method, external_domain=external, observed='HTML and accessible field labels; disabled questions are inventoried separately and not treated as active submissions')
            forms.append(info)
            if urlsplit(url).hostname == 'docs.google.com' and urlsplit(url).path.startswith('/forms/') and kinds & {'password','authentication secret','payment card'}:
                findings.append(finding(asset,'webpage','data_collection','hosted_form_secret_request','A hosted questionnaire requests account secrets or payment-card details. Google hosting does not verify its creator; verify the request independently before submitting.',.85,.85,metadata=info))
            if secrets and external:
                findings.append(finding(asset, 'webpage', 'phishing' if 'password' in kinds else 'data_collection', 'credential_destination_mismatch' if 'password' in kinds else 'sensitive_data_external_destination', 'A form requesting sensitive information declares a submission to another registrable domain. This can be legitimate outsourcing; verify the destination before submitting.', .85, .85, metadata=info))
            if kinds and scheme == 'http':
                findings.append(finding(asset, 'webpage', 'data_collection', 'unencrypted_data_submission', 'A form requests personal or sensitive data and declares an unencrypted HTTP destination.', .85 if secrets else .6, .9, metadata=info))
            if secrets and method == 'get':
                findings.append(finding(asset, 'webpage', 'data_collection', 'sensitive_data_in_url', 'A sensitive-data form declares GET submission, which can place entered data in URLs, browser history and server logs. JavaScript may change runtime behavior.', .75, .85, metadata=info))
    scripts = soup.find_all('script')[:100]
    third_party = sorted({urljoin(base, s['src'])[:2000] for s in scripts if s.get('src') and domain(urljoin(base, s['src'])) != domain(url)})[:30]
    inline = '\n'.join(s.get_text() for s in scripts if not s.get('src'))[:250000]
    references = [name for name, pattern in {
        'location access': r'geolocation\s*\.\s*(getCurrentPosition|watchPosition)',
        'camera or microphone access': r'getUserMedia\s*\(',
        'clipboard reading': r'clipboard\s*\.\s*read(Text)?\s*\(',
        'background beacon sending': r'sendBeacon\s*\(',
    }.items() if re.search(pattern, inline)]
    metadata = dict(forms=forms, third_party_scripts=third_party, script_api_references=references, limitations='Static HTML only. External scripts were not executed or inspected; runtime requests, actual data contents, cookies and user consent are not verified.')
    findings.append(finding(asset, 'webpage', 'data_collection', 'collection_surface', 'Inventoried declared form destinations, requested field types, third-party scripts and inline API references. Their presence alone is not data theft.', metadata=metadata))
    return metadata, findings
