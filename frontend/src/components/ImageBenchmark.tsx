import { useQuery } from '@tanstack/react-query';
type Metrics={count:number;genuine:number;synthetic:number;false_ai_accusations:number;missed_ai:number;ai_not_detected:number;inconclusive:number};
export default function ImageBenchmark(){
 const q=useQuery({queryKey:['image-benchmark'],queryFn:async()=>{const r=await fetch('/demo/image-evaluation.json');if(!r.ok)throw new Error('Benchmark unavailable');return await r.json() as {overall:Metrics;groups:Record<string,Metrics>;limitation:string};}});
 if(q.isPending)return <p>Loading image evaluation…</p>;
 if(q.isError)return <p>Image evaluation unavailable. No accuracy claim is shown.</p>;
 return <section className="card decision-brief"><h2>Image model: measured limitations</h2><p>{q.data.overall.count} additional research samples · fixed thresholds · no training on this evaluation</p><div className="decision-grid">{Object.entries(q.data.groups).map(([name,m])=><article key={name}><h3>{name}</h3><p>{m.synthetic-m.ai_not_detected}/{m.synthetic} AI images flagged</p><p>{m.false_ai_accusations}/{m.genuine} genuine images incorrectly flagged as AI</p><p>{m.missed_ai} AI images classified as non-AI · {m.inconclusive}/{m.count} total inconclusive</p></article>)}</div><p>{q.data.limitation}</p><a href="/demo/image-evaluation.json" download>Download evaluation summary</a></section>;
}
