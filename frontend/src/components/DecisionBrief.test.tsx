import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import DecisionBrief from './DecisionBrief';
import type { Analysis } from '../types';
test('presents evidence, actions and incomplete checks without inventing certainty',()=>{
 const row={report:{decision_summary:{title:'Limited evidence; security remains unresolved',meaning:'AI origin is assessed separately',findings:[],scenarios:[],actions:['Verify the sender'],gaps:['Scanner unavailable'],evidence_count:2,conflict_count:0}}} as unknown as Analysis;
 render(<DecisionBrief row={row}/>);
 expect(screen.getByText('Verify the sender')).toBeTruthy();
 expect(screen.getByText('Scanner unavailable')).toBeTruthy();
 expect(screen.getByText('AI origin is assessed separately')).toBeTruthy();
});
