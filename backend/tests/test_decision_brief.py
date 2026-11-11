from app.services.decision import decision_summary
from app.services.url_summary import summarize_url

def test_synthetic_does_not_become_security_finding():
    row={'report':{'evidence':[{'id':'ai','score':.999,'source':'image_detector','category':'synthetic_media'}]}}
    assert decision_summary(row)['findings']==[]

def test_failed_fetch_is_not_clean():
    summary=summarize_url('https://example.com', {'evidence':[], 'graph':{}})
    assert summary['title']=='Page inspection unavailable'
    assert not summary['page_inspected']

def test_canonical_root_and_gap_remain_visible():
    report={'graph':{'nodes':[{'id':'u','type':'url','label':'https://example.com/'}], 'edges':[{'source':'u','target':'p','relation':'contains'}]}, 'evidence':[{'id':'e','asset_id':'p','label':'page_metadata','metadata':{}},{'label':'unavailable','explanation':'Scanner unavailable'}]}
    summary=summarize_url('https://example.com#fragment',report)
    assert summary['page_inspected']
    assert 'coverage gaps' in summary['title']
    assert 'Scanner unavailable' in summary['gaps']

def test_readiness_reports_missing_dependencies(monkeypatch):
    from app.services import readiness as module
    monkeypatch.setattr(module, 'registry', lambda:[])
    monkeypatch.setattr(module, 'daemon_status', lambda _: {'available':False,'reason':'Not running'})
    result=module.readiness()
    assert next(c for c in result['checks'] if c['name']=='Image model')['status']=='attention'
    assert next(c for c in result['checks'] if c['name']=='Malware scanner')['action']
