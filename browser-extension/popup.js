const API='http://127.0.0.1:8000/api/v1';
const status=document.getElementById('status');
const button=document.getElementById('analyze');
let selected='';
(async()=>{const pending=await chrome.storage.session.get('selectedUrl');const [tab]=await chrome.tabs.query({active:true,currentWindow:true});selected=pending.selectedUrl||tab?.url||'';await chrome.storage.session.remove('selectedUrl');document.getElementById('url').textContent=selected;button.disabled=!/^https?:\/\//i.test(selected);})();
button.addEventListener('click',async()=>{
 button.disabled=true;status.textContent='Submitting URL…';
 try{
  const token=document.getElementById('token').value.trim();
  const headers={'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})};
  const submitted=await fetch(API+'/analyze/url',{method:'POST',headers,body:JSON.stringify({url:selected}),signal:AbortSignal.timeout(15000)});
  if(!submitted.ok)throw new Error(submitted.status===401?'This server requires authentication. Submit the URL in the signed-in web application.':'Submission failed: '+submitted.status);
  const {id}=await submitted.json();const link=document.getElementById('report');link.href='http://localhost:3000/analysis/'+encodeURIComponent(id);link.hidden=false;
  for(let i=0;i<60;i++){
   await new Promise(resolve=>setTimeout(resolve,2000));const response=await fetch(API+'/analyses/'+encodeURIComponent(id),{headers,signal:AbortSignal.timeout(10000)});if(!response.ok)throw new Error('Could not retrieve investigation');const row=await response.json();status.textContent=row.state;
   if(row.report){const r=row.report;status.textContent='Risk: '+r.risk_level+'\nEvidence confidence: '+Math.round(r.confidence*100)+'%\n'+(r.scenarios?.[0]?.label||'No supported fraud pattern identified')+'\n'+r.evidence.filter(e=>['high','critical'].includes(e.severity)).slice(0,3).map(e=>e.explanation).join('\n');return;}
   if(row.state==='FAILED')throw new Error(row.error||'Investigation failed');
  }
  status.textContent='Still processing. Open the full investigation for live status.';
 }catch(error){status.textContent=error.message;}finally{button.disabled=false;}
});
