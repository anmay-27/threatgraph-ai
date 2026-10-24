from app.analyzers.url.page import inspect_page


def inspect(html):
    return inspect_page(html.encode(), 'https://shop.example/', 'root')[1]


def test_unrelated_external_form_does_not_make_login_phishing():
    items = inspect('<form method="post" action="/login"><input type="password"></form><form action="https://newsletter.other/"><input type="email"></form>')
    assert not any(e.label == 'credential_destination_mismatch' for e in items)


def test_sensitive_destination_and_get_exposure_are_explained():
    items = inspect('<form action="http://collector.other/"><input name="card_number"><input name="cvv"></form>')
    assert {'sensitive_data_external_destination', 'sensitive_data_in_url', 'unencrypted_data_submission'} <= {e.label for e in items}
    assert all('value' not in str(e.metadata) for e in items)


def test_form_owner_base_and_submit_override_are_inspected():
    items = inspect('<base href="https://collector.other/"><form id="login" action="/submit" method="post"><button formaction="http://collector.other/submit">Send</button></form><input form="login" type="password" value="DO_NOT_COLLECT">')
    assert any(e.label == 'credential_destination_mismatch' for e in items)
    assert any(e.label == 'unencrypted_data_submission' for e in items)
    assert 'DO_NOT_COLLECT' not in str([e.metadata for e in items])


def test_permission_and_third_party_script_inventory_is_not_theft():
    items = inspect('<script src="https://analytics.other/a.js"></script><script>navigator.geolocation.getCurrentPosition(cb); navigator.sendBeacon("/stats", data)</script>')
    item = next(e for e in items if e.label == 'collection_surface')
    assert item.score is None
    assert len(item.metadata['script_api_references']) == 2
    assert item.metadata['third_party_scripts'] == ['https://analytics.other/a.js']
def test_dialog_does_not_submit_and_external_button_override_is_inspected():
    from bs4 import BeautifulSoup
    from app.analyzers.url.privacy import inspect_collection
    html = '<form method="dialog" action="http://other.test"><input type="password"></form><form id="login" method="post"><input type="password"></form><button form="login" formaction="http://other.test/collect">Go</button>'
    metadata, evidence = inspect_collection(BeautifulSoup(html, 'html.parser'), 'https://example.com', 'a')
    assert len(metadata['forms']) == 2
    assert sum(e.label == 'credential_destination_mismatch' for e in evidence) == 1

