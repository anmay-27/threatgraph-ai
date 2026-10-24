import '@testing-library/jest-dom/vitest';
import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,cleanup,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import Cases from './Cases';
import Message from './Message';
import {api} from '../api';
vi.mock('../api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
function show(component:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter>{component}</MemoryRouter></QueryClientProvider>)}
it('case creation shows server errors and does not invent a saved case',async()=>{
 vi.mocked(api).mockImplementation(async(path,options)=>{if(options)throw new Error('Database unavailable');return [] as any;});
 show(<Cases/>);fireEvent.change(screen.getByLabelText('New case title'),{target:{value:'Review an offer'}});fireEvent.click(screen.getByRole('button',{name:'Create case'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable');
});
it('message submission preserves content and exposes URL investigation notice',async()=>{
 vi.mocked(api).mockResolvedValue({id:'test-analysis'});
 show(<Message/>);fireEvent.change(screen.getByLabelText('Message content'),{target:{value:'Job offer: registration fee requested'}});fireEvent.click(screen.getByRole('button',{name:'Investigate message'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/analyze/message',expect.objectContaining({body:JSON.stringify({title:'Suspicious message',text:'Job offer: registration fee requested'})})));
 expect(screen.getByText(/Detected public URLs will be fetched/)).toBeVisible();
});
