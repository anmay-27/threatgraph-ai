import { Film, ScanEye } from 'lucide-react';
import type { Analysis } from '../types';

export default function VideoAssessment({ row }: { row: Analysis }) {
  const evidence = row.report?.evidence.find(e => e.source === 'video_detector');
  const score = evidence?.score;
  const available = typeof score === 'number';
  const details = evidence?.metadata || {};
  return <section className="card authenticity-card" aria-labelledby="video-origin-title">
    <div className="assessment-kicker"><span className="eyebrow"><Film size={16}/> VIDEO AUTHENTICITY</span><span className="research-pill">Experimental temporal screening</span></div>
    <h2 id="video-origin-title">{available ? 'Visual deepfake screening completed' : 'Video authenticity could not be assessed'}</h2>
    <p>{available ? 'A video model examined the sampled frames together. Its class suggestion is separate from malware risk and does not establish whether the video is authentic.' : evidence?.explanation || 'No video detector result is available.'}</p>
    {available && <><div className="authenticity-score"><strong>Model leans toward {score >= (details.threshold ?? .5) ? 'manipulated video' : 'real video'}</strong><span>Manipulation model score: <b>{(score * 100).toFixed(1)}%</b></span><progress max={1} value={score} aria-label="Video manipulation model score"/><small>Uncalibrated model output. This percentage is not the probability that the video is fake.</small></div>
    <div className="assessment-facts"><div><span>Sampled frames</span><strong>{details.sampled_frames ?? 'Unknown'}</strong><small>Across the full video</small></div><div><span>Frames with faces</span><strong>{details.face_frames ?? 'Unknown'}</strong><small>Domain check only</small></div><div><span>Conclusion</span><strong>Unverified</strong><small>Independent video validation pending</small></div></div>
    <details className="diagnostic-details"><summary><ScanEye size={16}/> What the model examined</summary><p>Sample times in seconds: {(details.sample_timestamps || []).map((t:number) => t.toFixed(2)).join(', ')}.</p><p>{details.limitations}</p><p>This model does not pinpoint a manipulated face region or frame. Audio cloning is a separate check.</p></details></>}
    <p>For verification, compare the original recording and its source, inspect signed provenance, and check whether the speech matches independently available recordings.</p>
  </section>;
}
