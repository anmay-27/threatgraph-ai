"""Real local account flow; temporary verification account is removed afterward."""
import json
import secrets
import sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path('research/results/account-ui');out.mkdir(parents=True,exist_ok=True)
email='ui-check-'+secrets.token_hex(8)+'@example.test'
password=secrets.token_urlsafe(24)
base='http://127.0.0.1:3000'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    context=browser.new_context(viewport={'width':1366,'height':900})
    page=context.new_page()
    page.goto(base)
    page.get_by_role('heading',name='Welcome back').wait_for()
    page.screenshot(path=str(out/'login-desktop.png'))
    page.get_by_role('button',name='New here? Create an account').click()
    page.get_by_label('Email address').fill(email)
    page.get_by_label('Password',exact=True).fill(password)
    page.get_by_label('Confirm password').fill('different-password')
    page.get_by_role('button',name='Create account',exact=True).click()
    page.get_by_text('Passwords do not match.',exact=True).wait_for()
    page.get_by_label('Confirm password').fill(password)
    page.get_by_role('button',name='Create account',exact=True).click()
    page.get_by_role('navigation',name='Main navigation').wait_for()
    me=context.request.get(base+'/api/v1/auth/me').json()
    assert me['email']==email and me['role']=='USER'
    with sqlite3.connect('storage/threatgraph.db') as db:
        stored=db.execute('SELECT password_hash FROM accounts WHERE email=?',(email,)).fetchone()[0]
        assert password not in stored and ':' in stored
    assert context.request.get(base+'/api/v1/cases').status==200
    assert context.request.get(base+'/api/v1/admin/users').status==403
    page.get_by_role('button',name='More pages').click()
    assert page.get_by_role('link',name='Operations').count()==0
    page.get_by_role('button',name='Log out',exact=True).click()
    page.get_by_role('heading',name='Welcome back').wait_for()
    assert context.request.get(base+'/api/v1/history').status==401
    page.get_by_label('Email address').fill(email)
    page.get_by_label('Password',exact=True).fill('incorrect-password')
    page.get_by_role('button',name='Log in',exact=True).click()
    page.get_by_text('Invalid email or password',exact=True).wait_for()
    page.get_by_label('Password',exact=True).fill(password)
    page.get_by_role('button',name='Log in',exact=True).click()
    page.get_by_role('navigation',name='Main navigation').wait_for()
    page.reload();page.get_by_role('navigation',name='Main navigation').wait_for()
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('navigation',name='Mobile navigation').get_by_role('button',name='More navigation').click()
    page.get_by_role('button',name='Log out',exact=True).click()
    page.get_by_role('heading',name='Welcome back').wait_for()
    page.wait_for_function('document.documentElement.scrollWidth <= innerWidth+1')
    page.screenshot(path=str(out/'login-mobile.png'),full_page=True)
    page.route('**/api/v1/auth/me',lambda route:route.fulfill(status=503,json={'detail':'Temporary verification outage'}))
    page.reload();page.get_by_role('heading',name='Workspace temporarily unavailable').wait_for()
    page.unroute('**/api/v1/auth/me')
    page.get_by_role('button',name='Try again').click()
    page.get_by_role('heading',name='Welcome back').wait_for()
    browser.close()
with sqlite3.connect('storage/threatgraph.db') as db:
    db.execute('DELETE FROM login_sessions WHERE account_id=?',(me['id'],))
    db.execute('DELETE FROM accounts WHERE id=? AND email=?',(me['id'],email))
(out/'verification.json').write_text(json.dumps(dict(signup=True,password_mismatch=True,wrong_password=True,persistence=True,session_reload=True,logout=True,mobile=True,service_error=True,admin_hidden=True,temporary_account_removed=True),indent=2))
print('Account browser verification passed; temporary account removed.')
