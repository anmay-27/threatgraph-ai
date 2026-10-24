from app.analyzers.url.page import inspect_page


def test_google_style_labels_expose_personal_data_without_claiming_theft():
    html=b'''<html><form action="/forms/d/e/example/formResponse" method="post">
    <div role="listitem"><div role="heading" id="q1">Your full name</div><input name="entry.1" aria-labelledby="q1" value="Never retain this"></div>
    <div role="listitem"><div role="heading" id="q2">Mobile number</div><input name="entry.2" aria-labelledby="q2"></div>
    <label for="mail">Email address</label><input id="mail" name="entry.3">
    <input type="hidden" name="password_warning" value="Never submit passwords">
    </form></html>'''
    page,evidence,_=inspect_page(html,'https://docs.google.com/forms/d/e/example/viewform','a')
    form=page['data_collection']['forms'][0]
    assert form['field_types']==['email','name','phone']
    assert 'Never retain this' not in str(form)
    assert not any(e.score is not None for e in evidence)


def test_hosted_questionnaire_secrets_are_flagged_even_on_google_domain():
    html=b'<html><form method="post"><label for="q">Your password</label><input id="q" name="entry.1"></form></html>'
    _,evidence,_=inspect_page(html,'https://docs.google.com/forms/d/e/example/viewform','a')
    assert any(e.label=='hosted_form_secret_request' for e in evidence)


def test_ordinary_login_is_not_a_hosted_questionnaire():
    _,evidence,_=inspect_page(b'<html><form method="post"><input type="password"></form></html>','https://accounts.google.com/signin','a')
    assert not any(e.label=='hosted_form_secret_request' for e in evidence)


def test_disabled_preview_questions_are_inventory_not_active_submission():
    html=b'<html><form><label for="phone">Phone Number</label><input disabled id="phone"></form></html>'
    page,evidence,_=inspect_page(html,'https://docs.google.com/forms/d/e/example/viewform','a')
    form=page['data_collection']['forms'][0]
    assert form['field_types']==[]
    assert form['displayed_field_types']==['phone']
    assert form['fields'][0]['disabled'] is True
    assert not any(e.score is not None for e in evidence)

def test_disabled_fieldset_cannot_create_secret_submission_finding():
    html=b'<form action="http://other.example" method="get"><fieldset disabled><input type="password"><button formaction="https://third.example">Send</button></fieldset></form>'
    page,evidence,_=inspect_page(html,'https://example.com','a')
    assert page['data_collection']['forms'][0]['field_types']==[]
    assert not any(e.label in {'credential_destination_mismatch','sensitive_data_in_url','unencrypted_data_submission'} for e in evidence)

def test_first_legend_exception_remains_active():
    html=b'<form action="http://other.example"><fieldset disabled><legend><input type="password"></legend></fieldset></form>'
    _,evidence,_=inspect_page(html,'https://example.com','a')
    assert any(e.label=='credential_destination_mismatch' for e in evidence)
