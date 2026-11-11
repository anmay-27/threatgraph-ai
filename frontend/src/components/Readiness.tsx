import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
export default function Readiness(){
 const q=useQuery({queryKey:['readiness'],queryFn:async()=>{const data=await api<{checks:{name:string;status:string;detail:string;action:string}[];scope:string}>('/readiness');if(!Array.isArray(data.checks))throw new Error('Invalid readiness response');return data;},refetchInterval:30000,retry:1});
 return <section className="card readiness-panel" aria-label="Before you investigate"><details><summary>Before you investigate · {q.isPending?'Checking capabilities…':q.isError?'Readiness check failed':`${q.data.checks.filter(c=>c.status==='attention').length} items need attention`}</summary>{q.isError?<p role="alert">Cannot check capabilities. Confirm the API is running, then <button onClick={()=>q.refetch()}>Retry</button>.</p>:q.data&&<><p>{q.data.scope}</p><div className="decision-grid">{q.data.checks.map(c=><article key={c.name}><strong>{c.status==='ready'?'✓':'!'} {c.name}</strong><p>{c.detail}</p>{c.action&&<p><strong>Next step:</strong> {c.action}</p>}</article>)}</div></>}</details></section>;
}
