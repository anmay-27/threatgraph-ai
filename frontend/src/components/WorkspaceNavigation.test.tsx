import { beforeAll, afterEach, expect, test, vi } from 'vitest';
import { render, screen, cleanup, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WorkspaceNavigation from './WorkspaceNavigation';
vi.mock('./CommandMenu',()=>({default:()=> <button>Search</button>}));
vi.mock('./ThemeToggle',()=>({default:()=> <button>Theme</button>}));
afterEach(cleanup);
// jsdom does not implement the native dialog API; real dismissal is browser-tested.
beforeAll(()=>{HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};});
test('analyst navigation exposes cases and moves graph into mobile More',()=>{
 render(<MemoryRouter initialEntries={['/cases']}><WorkspaceNavigation role="ANALYST" connected offline={false}/></MemoryRouter>);
 const main=within(screen.getByRole('navigation',{name:'Main navigation'}));
 expect(main.getByRole('link',{name:'Cases'}).getAttribute('aria-current')).toBe('page');
 expect(main.getByRole('link',{name:'Graph'})).toBeTruthy();
 const mobile=within(screen.getByRole('navigation',{name:'Mobile navigation'}));
 expect(mobile.queryByRole('link',{name:'Graph'})).toBeNull();
 expect(screen.queryByRole('link',{name:'Operations',hidden:true})).toBeNull();
});
test('signed-out navigation does not expose case or intelligence links',()=>{
 render(<MemoryRouter><WorkspaceNavigation connected={false} offline/></MemoryRouter>);
 expect(screen.queryByRole('link',{name:'Cases',hidden:true})).toBeNull();
 expect(screen.queryByRole('link',{name:'Intelligence graph',hidden:true})).toBeNull();
 expect(screen.getByText('Offline')).toBeTruthy();
});
