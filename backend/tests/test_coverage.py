from app.services.coverage import investigation_checks
from app.schemas.evidence import finding


def test_missing_video_checkpoint_is_not_a_completed_deepfake_check():
    items = [finding('a', 'video_detector', 'synthetic_media', 'unavailable', 'No trained checkpoint installed')]
    checks = investigation_checks([{'type':'video'}], items)
    video = next(c for c in checks if c['id'] == 'video')
    assert video['status'] == 'unavailable'
    assert video['unavailable_reasons'] == ['No trained checkpoint installed']
    assert next(c for c in checks if c['id'] == 'malware')['status'] == 'not_checked'


def test_a_page_block_is_not_a_completed_phishing_or_collection_check():
    items = [finding('a', 'safe_fetch', 'metadata', 'unavailable', 'HTTP 403')]
    checks = investigation_checks([{'type':'url'}], items)
    assert next(c for c in checks if c['id'] == 'phishing')['status'] == 'unavailable'
    assert next(c for c in checks if c['id'] == 'collection')['status'] == 'not_checked'


def test_collection_inventory_is_neutral_but_exposure_is_a_finding():
    items = [finding('a','webpage','data_collection','collection_surface','Inventory')]
    checks = investigation_checks([{'type':'webpage'}],items)
    assert next(c for c in checks if c['id'] == 'collection')['status'] == 'completed'
    items.append(finding('a','webpage','data_collection','sensitive_data_in_url','GET password',.75,.85))
    checks = investigation_checks([{'type':'webpage'}],items)
    assert next(c for c in checks if c['id'] == 'collection')['status'] == 'findings'
