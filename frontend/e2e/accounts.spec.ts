import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

const root=resolve('..');
const python=resolve('../.venv/Scripts/python.exe');
const api='http://127.0.0.1:8001/api/v1';
const site='http://127.0.0.1:3001';
function promote(email:string){execFileSync(python,['scripts/manage_account.py',email,'--role','ANALYST'],{cwd:root,env:{...process.env,DATABASE_URL:'sqlite:///./storage/auth-browser.db'}});}
async function registerAndLogin(page:any,email:string){
 await page.goto(site);
 await page.getByLabel('Email').fill(email);
 await page.getByLabel('Password (at least 12 characters)').fill('test-password-with-entropy');
 await page.getByRole('button',{name:'Create an account'}).click();
 await page.getByRole('button',{name:'Create account'}).click();
 await expect(page.getByText(email,{exact:false})).toBeVisible();
}

test('separate signed-in analysts cannot open each other\'s cases; bearer token is scoped',async({page,request})=>{
 test.setTimeout(90000);
 const stamp=Date.now();const first=`first-${stamp}@example.test`,second=`second-${stamp}@example.test`;
 await registerAndLogin(page,first);
 await expect(page.getByRole('link',{name:'Cases',exact:true})).toHaveCount(0);
 promote(first);
 await page.getByRole('button',{name:'Sign out & revoke tokens'}).click();
 await page.getByLabel('Email').fill(first);await page.getByLabel('Password (at least 12 characters)').fill('test-password-with-entropy');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('button',{name:'Sign out & revoke tokens'})).toBeVisible();
 await page.goto(site+'/cases');
 await page.getByLabel('New case title').fill('Private recruitment case');await page.getByRole('button',{name:'Create case'}).click();
 await expect(page).toHaveURL(/cases\//);const caseId=page.url().split('/').pop()!;
 await page.getByRole('button',{name:'Create extension token'}).click();
 await expect(page.getByLabel('Private token (expires in 12 hours)')).toBeVisible();
 const token=await page.getByLabel('Private token (expires in 12 hours)').inputValue();
 expect(token.length).toBeGreaterThan(32);
 const firstResponse=await request.get(api+'/cases/'+caseId,{headers:{Authorization:'Bearer '+token}});expect(firstResponse.status()).toBe(200);
 await page.getByRole('button',{name:'Sign out & revoke tokens'}).click();
 await expect(page.getByLabel('Email')).toBeVisible();
 const revoked=await request.get(api+'/cases/'+caseId,{headers:{Authorization:'Bearer '+token}});expect(revoked.status()).toBe(401);
 await registerAndLogin(page,second);
 promote(second);
 await page.getByRole('button',{name:'Sign out & revoke tokens'}).click();
 await page.getByLabel('Email').fill(second);await page.getByLabel('Password (at least 12 characters)').fill('test-password-with-entropy');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('button',{name:'Sign out & revoke tokens'})).toBeVisible();
 await page.goto(site+'/cases/'+caseId);
 await expect(page.getByRole('alert')).toContainText('Case not found');
 await page.goto(site+'/cases');await expect(page.getByText('Private recruitment case')).toHaveCount(0);
});
