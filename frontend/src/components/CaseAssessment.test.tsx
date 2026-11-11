// @vitest-environment jsdom
import { it, expect } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CaseAssessment from './CaseAssessment';

it('shows case hypotheses and keeps synthetic origin separate in both views',()=>{
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><CaseAssessment caseId="case" data={{title:'Potential fraud chain requires review',scope:'Saved evidence',total:1,completed:0,partial:1,scenarios:[{id:'s',label:'Recruitment payment chain',explanation:'Observed attachment path',analysis_id:'a',evidence_ids:['e1','e2'],missing_evidence:['Employer identity']}],correlations:[{case_id:'old',case_title:'Previous case',entity_id:'upi',entity_type:'UPI_ID',value:'training@demo',significance:'Not proof of fraud'}],conflicts:[],gaps:[{analysis_id:'a',reason:'Scanner unavailable'}],recommendations:['Verify employer independently'],synthetic_findings:[]}}/></MemoryRouter></QueryClientProvider>);
  expect(screen.getByText('Recruitment payment chain')).toBeTruthy();
  expect(screen.getByText('Previous case').getAttribute('href')).toBe('/cases/old');
  fireEvent.click(screen.getByRole('button',{name:'Switch to analyst view'}));
  expect(screen.getByText('Evidence references: e1, e2')).toBeTruthy();
  expect(screen.getByText(/does not increase the cybersecurity risk/)).toBeTruthy();
  cleanup();
});
