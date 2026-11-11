import InvestigationJourney from "../components/InvestigationJourney";
import Readiness from "../components/Readiness";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  FileSearch,
  Link2,
  Loader2,
  ScanLine,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Image, AudioLines, Globe, FileCheck2, X, Sparkles } from "lucide-react";

import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Analysis } from "../types";

import { AnalysisTable, ErrorBox, Loading, client } from "../components/shared";
export default function Analyze() {
  const [tab, setTab] = useState("url"),
    [url, setUrl] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [drag, setDrag] = useState(false);
  const [selectedShortcut, setSelectedShortcut] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [intent, setIntent] = useState("Explore a link or drop a file. Let’s follow the evidence.");
  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) { setPreview(null); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const navigate = useNavigate();
  const capabilities = useQuery({ queryKey: ['models'], queryFn: () => api<{name:string; available:boolean; deployment_status?:string}[]>('/models') });
  const health = useQuery({ queryKey: ['scan-health'], queryFn: () => api<{max_upload_mb?:number; malware_scanner?:{available:boolean}}>('/health'), refetchInterval:30000 });
  const maxUpload = health.data?.max_upload_mb ?? 250;
  const oversized = !!file && file.size > maxUpload * 1024 * 1024;
  const modality = file?.type.split('/')[0];
  const detector = capabilities.data?.find(model => model.name === modality);
  const mutation = useMutation({
    mutationFn: async () => {
      if (tab === "url")
        return api<{ id: string }>("/analyze/url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });
      if (!file) throw new Error("Select a file first.");
      if (oversized) throw new Error(`Choose a file smaller than ${maxUpload} MB.`);
      const body = new FormData();
      body.append("file", file);
      return api<{ id: string }>("/analyze/file", { method: "POST", body });
    },
    onSuccess: (result) => {
      client.invalidateQueries({ queryKey: ["history"] });
      navigate("/analysis/" + result.id);
    },
  });
  const recent = useQuery({
    queryKey: ["history", "recent"],
    queryFn: () => api<Analysis[]>("/history?limit=3"),
  });
  return (
    <>
      <section className="visual-hero" aria-label="Digital investigation workspace">
        <div className="visual-hero-copy"><span className="eyebrow">THREATGRAPH / INVESTIGATION STUDIO</span><h1>Look closer.<br/><em>Connect the clues.</em></h1><p>Turn suspicious links, images and documents into evidence you can understand.</p><div className="hero-actions"><a className="hero-start" href="#investigation-input">Start investigating <ArrowRight size={17}/></a><Link to="/demo">See it in action <ArrowUpRight size={16}/></Link></div><div className="hero-trust"><ShieldCheck size={15}/> Local analysis <span>&middot;</span> Evidence-led findings</div></div>
        <div className="visual-hero-art"><img src="/art/investigation-hero.png" alt="" fetchPriority="high" width="1536" height="1024"/><span className="art-caption">Every clue has a connection.</span></div>
      </section>
      <div className="landing-actions">
        <Link to="/demo">First time? Try the guided demo <ArrowUpRight size={15}/></Link>
        <Link to="/messages">Analyze a suspicious message <ArrowUpRight size={15}/></Link>
        <Link to="/messages?kind=email">Investigate an email <ArrowUpRight size={15}/></Link>
      </div>
      <div className="quick-prompts" aria-label="Investigation shortcuts">
        {[
          { icon: Image, title: "Is this image AI?", type: "file", accept: "image/*", hint: "Upload an image to explore AI-generation signals and provenance." },
          { icon: Globe, title: "Can I trust this link?", type: "url", accept: "", hint: "Paste a link to investigate its destination and connected evidence." },
          { icon: AudioLines, title: "Explore audio or video", type: "file", accept: "audio/*,video/*", hint: "Inspect media metadata and available detectors. Coverage is shown in your report." },
          { icon: FileCheck2, title: "Inspect a document", type: "file", accept: "", hint: "Upload a document to inspect its file properties and available evidence." },
        ].map(({ icon: Icon, title, type, accept, hint }, index) => <button key={title} aria-pressed={selectedShortcut===title} onClick={() => { setSelectedShortcut(title); setTab(type); setIntent(hint); requestAnimationFrame(() => { document.getElementById('investigation-input')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}); if (type === "file" && input.current) { input.current.accept = accept; input.current.click(); } else document.getElementById("url")?.focus({preventScroll:true}); }); }}><Icon size={19} /><span><strong>{title}</strong><small>{['Image authenticity','Website & redirect checks','Experimental media checks','PDFs, files & hidden links'][index]}</small></span><ArrowUpRight size={14} /></button>)}
      </div>
      <div id="investigation-input" className="submission-layout">
        <section className="card submission">
          <div className="tabs" role="tablist" aria-label="Submission type">
            <button
              role="tab"
              aria-selected={tab === "url"}
              onClick={() => setTab("url")}
              className={tab === "url" ? "active" : ""}
            >
              <Link2 size={17} />
              Analyze a URL
            </button>
            <button
              role="tab"
              aria-selected={tab === "file"}
              onClick={() => setTab("file")}
              className={tab === "file" ? "active" : ""}
            >
              <Upload size={17} />
              Upload a file
            </button>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
          >
            {tab === "url" ? (
              <div className="input-area">
                <label htmlFor="url">Where should we start?</label><p className="intent-hint" aria-live="polite">{intent}</p>
                <div className="url-field">
                  <Link2 size={19} />
                  <input
                    id="url"
                    type="url"
                    required
                    placeholder="https://example.com/page-or-media"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </div>
                <p className="hint">
                  Paste a webpage, image, audio, video, or file URL.
                </p>
              </div>
            ) : (
              <div className="input-area">
                <label htmlFor="file">Choose content to investigate</label>
                <div
                  className={`dropzone ${drag ? "dragging" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDrag(false);
                    setFile(e.dataTransfer.files[0] || null);
                  }}
                >
                  <Upload size={28} />
                  <strong>{file ? file.name : "Drop a file here"}</strong>
                  {preview && <img className="upload-preview" src={preview} alt="Selected image preview" />}
                  {file && <div className="attachment-meta"><span>{(file.size / 1024 / 1024).toFixed(2)} MB · Ready to investigate</span><button type="button" aria-label="Remove selected file" onClick={() => { setFile(null); if (input.current) input.current.value = ""; }}><X size={15} /></button></div>}
                  <button type="button" onClick={() => input.current?.click()}>
                    or browse files
                  </button>
                  <input
                    ref={input}
                    id="file"
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                  <small>
                    Images, audio, video, PDF, and other files · up to {maxUpload} MB
                  </small>
                </div>
              </div>
            )}
            {mutation.isError && <ErrorBox error={mutation.error} />}
            {tab === 'file' && oversized && <div role="alert" className="notice error">This file exceeds the {maxUpload} MB limit. Choose a smaller file.</div>}
            {file && ['image','video','audio'].includes(modality || '') && capabilities.data && <p className="hint" role="status">{detector?.available ? `${modality === 'video' ? 'Experimental video' : modality === 'audio' ? 'Experimental audio' : 'Research image'} detector available. Review the model result and its limits in the report.` : `${modality === 'audio' ? 'Audio' : modality === 'video' ? 'Video' : 'Image'} authenticity detector unavailable. This investigation can still inspect file metadata and available security checks.`}</p>}
            {health.data && <p className="hint" role="status">Malware signatures: {health.data.malware_scanner?.available ? 'scanner ready' : 'scanner unavailable; a malware verdict will be missing'}.</p>}
            <div className="submit-bottom">
              <span>
                <ShieldCheck size={16} />
                Private files stay local
              </span>
              <button
                className="primary"
                disabled={mutation.isPending || (tab === "file" && (!file || oversized)) || (tab === "url" && !url.trim())}
              >
                {mutation.isPending ? (
                  <Loader2 className="spin" size={17} />
                ) : (
                  <ScanLine size={17} />
                )}
                Start investigation
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        </section>
        <aside className="case-story"><img src="/art/offer-investigation.png" alt="" loading="lazy" width="1536" height="1024"/><div><span className="eyebrow">TRY A REAL WORKFLOW</span><h2>A job offer.<br/>A hidden connection.</h2><p>Follow a fictional email through its attachment, QR code and shared payment identifier.</p><Link to="/demo">Explore the guided case <ArrowUpRight size={16}/></Link></div></aside>
      </div>
      <Readiness/>
      <InvestigationJourney/>
      <div className="composer-note"><Sparkles size={13} /> Real evidence. Transparent uncertainty. Your files stay local.</div>
      <div className="capabilities">
        {[
          [
            "01",
            "Trace hidden connections",
            "Discover redirects and QR destinations with bounded, defensive fetching.",
          ],
          [
            "02",
            "Inspect content authenticity",
            "Combine available models with metadata and provenance inspection.",
          ],
          [
            "03",
            "Understand uncertainty",
            "See coverage gaps and conflicting signals before making a decision.",
          ],
        ].map(([n, title, description]) => (
          <article key={n}>
            <span>{n}</span>
            <h3>{title}</h3>
            <p>{description}</p>
          </article>
        ))}
      </div>
      <section className="recent">
        <div className="section-heading">
          <h2>Recent investigations</h2>
          <Link to="/history">
            View history <ArrowRight size={15} />
          </Link>
        </div>
        {recent.isError ? (
          <ErrorBox error={recent.error} />
        ) : recent.isPending ? (
          <Loading />
        ) : recent.data.length ? (
          <AnalysisTable rows={recent.data} />
        ) : (
          <div className="empty-inline">
            <FileSearch size={20} />
            <div>
              <strong>Your first investigation starts here</strong>
              <p>
                Submit content above. Your findings and evidence will appear in
                this workspace.
              </p>
            </div>
            <span>NO ANALYSES YET</span>
          </div>
        )}
      </section>
    </>
  );
}
