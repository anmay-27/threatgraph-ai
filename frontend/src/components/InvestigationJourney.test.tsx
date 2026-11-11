import { test, expect } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import InvestigationJourney from './InvestigationJourney';
test('guide changes its explanation and destination with keyboard navigation',()=>{
 render(<MemoryRouter><InvestigationJourney/></MemoryRouter>);
 const first=screen.getByRole('tab',{name:/Start with a clue/});
 fireEvent.keyDown(first,{key:'ArrowRight'});
 expect(screen.getByRole('tab',{name:/Connect the evidence/}).getAttribute('aria-selected')).toBe('true');
 expect(screen.getByRole('link',{name:/Explore your cases/}).getAttribute('href')).toBe('/cases');
 cleanup();
});
