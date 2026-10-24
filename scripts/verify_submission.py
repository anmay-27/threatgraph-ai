"""Exercise the actual local UI at presentation and mobile widths."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

output = Path('research/results/submission')
output.mkdir(parents=True, exist_ok=True)
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    for theme in ['light', 'dark']:
        for width in [1440, 390]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto('http://127.0.0.1:3000')
            page.evaluate('(theme) => localStorage.setItem("threatgraph-theme", theme)', theme)
            page.reload()
            page.get_by_role('button', name='Start investigation', exact=True).wait_for()
            assert page.get_by_role('button', name='Start investigation', exact=True).is_disabled()
            for route in ['/analyze', '/demo', '/dashboard', '/history']:
                page.goto('http://127.0.0.1:3000' + route)
                page.locator('main h1').wait_for()
                page.wait_for_timeout(500)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'Overflow: {route} {width}'
                checks.append({'route': route, 'theme': theme, 'width': width})
                if route in ['/analyze', '/demo']:
                    page.screenshot(path=str(output / f'{route[1:]}-{theme}-{width}.png'))
    page.goto('http://127.0.0.1:3000/demo')
    sample = page.locator('blockquote').inner_text()
    page.goto('http://127.0.0.1:3000/messages')
    page.get_by_label('Investigation title', exact=True).fill('Submission demo — fictional recruitment message')
    page.get_by_label('Message content', exact=True).fill(sample)
    page.get_by_role('button', name='Investigate message', exact=True).click()
    page.wait_for_url('**/analysis/**', timeout=30000)
    identifier = page.url.rsplit('/', 1)[-1]
    page.get_by_role('link', name='Export PDF', exact=True).wait_for(timeout=60000)
    investigation = page.request.get(f'http://127.0.0.1:3000/api/v1/analyses/{identifier}').json()
    assert any(item['label'] == 'advance_fee_request' for item in investigation['report']['evidence'])
    response = page.request.get(f'http://127.0.0.1:3000/api/v1/analyses/{identifier}/report.pdf')
    assert response.ok and response.body().startswith(b'%PDF')
    (output / 'demo-report.pdf').write_bytes(response.body())
    assert not errors, errors
    browser.close()
(output / 'validation.json').write_text(json.dumps({'checks': checks, 'message_analysis': identifier, 'pdf': True, 'console_errors': errors, 'passed': True}, indent=2))
print(json.dumps({'responsive_checks': len(checks), 'message_analysis': identifier, 'pdf': True, 'passed': True}))
