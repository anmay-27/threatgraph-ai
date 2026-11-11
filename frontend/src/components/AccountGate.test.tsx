import {afterEach, expect, test, vi} from 'vitest';
import {render, screen, cleanup} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import AccountGate from './AccountGate';
import {api, ApiError} from '../api';
vi.mock('../api',async importOriginal=>({...await importOriginal<typeof import('../api')>(),api:vi.fn()}));
afterEach(()=>{cleanup();window.history.replaceState({},'', '/');});
function show(enabled:boolean){
 vi.mocked(api).mockImplementation(async path=>{if(path==='/auth/providers')return {google:enabled} as never;throw new ApiError('Sign in',401);});
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AccountGate><p>Private workspace</p></AccountGate></QueryClientProvider>);
}
test('configured Google login is available alongside password login',async()=>{
 show(true);
 expect((await screen.findByRole('button',{name:'Continue with Google'}) as HTMLButtonElement).disabled).toBe(false);
 expect(screen.getByLabelText('Email address')).toBeTruthy();
 expect(screen.queryByText('Private workspace')).toBeNull();
});
test('unconfigured Google login explains setup and preserves password login',async()=>{
 show(false);
 expect((await screen.findByRole('button',{name:'Continue with Google'}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByText(/awaiting configuration/)).toBeTruthy();
});
test('callback conflict explains how to access existing account',async()=>{
 window.history.replaceState({},'', '/?auth_error=existing_account');show(true);
 expect((await screen.findByRole('alert')).textContent).toContain('existing password');
});
