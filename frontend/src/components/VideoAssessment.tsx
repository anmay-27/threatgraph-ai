import { Film, ScanEye } from 'lucide-react';
import type { Analysis } from '../types';

export default function VideoAssessment({ row }: { row: Analysis }) {
  const evidence = row.report?.evidence.find(e => e.source === 'video_detector');
  const score = evidence?.score;
  const available = typeof score === 'number';
  const details = evidence?.metadata || {};
  const video = row.report?.evidence.find(e=>e.label==='video_metadata')?.metadata;
  const scanned = row.report?.evidence.some(e=>e.source==='clamav' && e.label==='no_signature_match');
  return <section className="card authenticity-card" aria-labelledby="video-origin-title">
    <div className="assessment-kicker"><span className="eyebrow"><Film size={16}/> VIDEO AUTHENTICITY</span><span className="research-pill">Experimental temporal screening</span></div>
    <h2 id="video-origin-title">{available ? 'Visual deepfake screening completed' : 'Video authenticity could not be assessed'}</h2>
    <p>{available ? 'A video model examined the sampled frames together. Its class suggestion is separate from malware risk and does not establish whether the video is authentic.' : evidence?.explanation || 'No video detector result is available.'}</p>
    {video && <div className="assessment-facts"><div><span>Video decoded</span><strong>{Number(video.duration).toFixed(1)} sec</strong><small>{Number(video.fps).toFixed(1)} frames per second</small></div><div><span>Content inspection</span><strong>Frames sampled</strong><small>QR and available model checks</small></div><div><span>Malware signatures</span><strong>{scanned ? 'No match found' : 'See security checks'}</strong><small>Separate from video authenticity</small></div></div>}
    {!available && <p>The installed deepfake model needs visible faces in enough sampled frames. Animation, screen recordings, landscapes, and fully generated scenes may fall outside its supported scope.</p>}
    {available && <><div className="authenticity-score"><strong>Model leans toward {score >= (details.threshold ?? .5) ? 'manipulated video' : 'real video'}</strong><span>Manipulation model score: <b>{(score * 100).toFixed(1)}%</b></span><progress max={1} value={score} aria-label="Video manipulation model score"/><small>Uncalibrated model output. This percentage is not the probability that the video is fake.</small></div>
    <div className="assessment-facts"><div><span>Sampled frames</span><strong>{details.sampled_frames ?? 'Unknown'}</strong><small>Across the full video</small></div><div><span>Frames with faces</span><strong>{details.face_frames ?? 'Unknown'}</strong><small>Domain check only</small></div><div><span>Conclusion</span><strong>Unverified</strong><small>Independent video validation pending</small></div></div>
    <details className="diagnostic-details"><summary><ScanEye size={16}/> What the model examined</summary><p>Sample times in seconds: {(details.sample_timestamps || []).map((t:number) => t.toFixed(2)).join(', ')}.</p><p>{details.limitations}</p><p>This model does not pinpoint a manipulated face region or frame. Audio cloning is a separate check.</p></details></>}
    <p>For verification, compare the original recording and its source, inspect signed provenance, and check whether the speech matches independently available recordings.</p>
  </section>;
}
