import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, ArrowUpRight, X } from "lucide-react";
import { api } from "../api";
import type { Analysis } from "../types";

export default function CommandMenu() {
  const dialog = useRef<HTMLDialogElement>(null);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const history = useQuery({ queryKey: ["history", "commands"], queryFn: () => api<Analysis[]>("/history?limit=30") });
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); dialog.current?.showModal(); } };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  const links = [
    { name: "Start a new investigation", path: "/analyze" },
    { name: "Explore your dashboard", path: "/dashboard" },
    { name: "Browse analysis history", path: "/history" },
    ...(history.data || []).map((row) => ({ name: row.name, path: "/analysis/" + row.id })),
  ].filter((row) => row.name.toLowerCase().includes(search.toLowerCase()));
  return <>
    <button className="command-trigger" aria-label="Search workspace" onClick={() => dialog.current?.showModal()}><Search size={16} /><span>Search workspace</span><kbd>Ctrl K</kbd></button>
    <dialog ref={dialog} className="command-dialog" aria-label="Search workspace" onClick={(e) => { if (e.target === dialog.current) dialog.current.close(); }}>
      <div className="command-input"><Search size={20} /><input autoFocus aria-label="Search investigations and pages" placeholder="Find an investigation or jump to a page…" value={search} onChange={(e) => setSearch(e.target.value)} /><button aria-label="Close search" onClick={() => dialog.current?.close()}><X size={18} /></button></div>
      <div className="command-results">{links.length ? links.map((row) => <button key={row.path} onClick={() => { navigate(row.path); dialog.current?.close(); setSearch(""); }}><span>{row.name}</span><ArrowUpRight size={16} /></button>) : <p>No matching investigations.</p>}</div>
      <small>Search your latest 30 investigations · Esc to close</small>
    </dialog>
  </>;
}
