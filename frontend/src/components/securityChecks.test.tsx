import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import SecurityChecks from './SecurityChecks';
import VideoAssessment from './VideoAssessment';
import type { Analysis } from '../types';
afterEach(cleanup);
it('distinguishes missing checks from completed checks and exposes the reason', () => {
  const row = {report: {evidence: [], checks: [{id:'video', title:'Visual deepfake', status:'unavailable', summary:'Check could not complete', evidence_ids:[], limitations:'Not a proof of authenticity', unavailable_reasons:['No faces found']} ]}} as unknown as Analysis;
  render(<SecurityChecks row={row}/>);
  expect(screen.getByText('Unavailable')).toBeVisible();
  expect(screen.getByText('No faces found')).toBeInTheDocument();
});
it('does not promote a high uncalibrated video score to a verified finding', () => {
  const row = {report:{evidence:[{source:'video_detector', score:.99, metadata:{threshold:.5, sampled_frames:16, face_frames:16, sample_timestamps:[0,1]}}]}} as unknown as Analysis;
  render(<VideoAssessment row={row}/>);
  expect(screen.getByText('Unverified')).toBeVisible();
  expect(screen.getByText(/not the probability/)).toBeVisible();
  expect(screen.getByText(/Model leans toward manipulated/)).toBeVisible();
});
