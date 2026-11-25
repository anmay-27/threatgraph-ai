from fastapi.testclient import TestClient
from scripts import hosted_app


def test_hosted_frontend_does_not_swallow_api_errors(tmp_path, monkeypatch):
    (tmp_path/'index.html').write_text('<html>ThreatGraph test</html>')
    (tmp_path/'asset.js').write_text('console.log("fixture")')
    monkeypatch.setattr(hosted_app, 'DIST', tmp_path)
    with TestClient(hosted_app.app) as client:
        assert 'ThreatGraph test' in client.get('/cases').text
        assert client.get('/asset.js').status_code == 200
        assert client.get('/missing.js').status_code == 404
        assert client.get('/api/v1/nonexistent').status_code == 404
        assert client.get('/api/v1/health').json()['status'] == 'ok'
