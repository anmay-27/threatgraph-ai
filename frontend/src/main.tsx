import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BookOpen,
  Boxes,
  History,
  LayoutDashboard,
  Network,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import { PanelLeftClose, PanelLeftOpen, Plus, Sparkles } from "lucide-react";
import CommandMenu from "./components/CommandMenu";
import ThemeToggle from "./components/ThemeToggle";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import "@fontsource-variable/manrope";
import "./styles.css";
import "./studio.css";
import "./theme.css";
import "./cases.css";

import { client, Empty } from "./components/shared";
import Analyze from "./pages/Analyze";
import Dashboard from "./pages/Dashboard";
import HistoryPage from "./pages/HistoryPage";
import Methodology from "./pages/Methodology";
import Models from "./pages/Models";
import Result from "./pages/Result";
import Cases, { CasePage } from "./pages/Cases";
import Intelligence, { EntityPage } from "./pages/Intelligence";
import Message from "./pages/Message";
import AccountGate from "./components/AccountGate";
import Operations from "./pages/Operations";
function Shell() {
  const account = useQuery({
    queryKey: ["account"],
    queryFn: () => api<{ role: string }>("/auth/me"),
  });
  const [collapsed, setCollapsed] = useState(() => window.innerWidth <= 760);
  useEffect(() => {
    const breakpoint = window.matchMedia("(max-width: 760px)");
    const collapseOnMobile = () => {
      if (breakpoint.matches) setCollapsed(true);
    };
    breakpoint.addEventListener("change", collapseOnMobile);
    return () => breakpoint.removeEventListener("change", collapseOnMobile);
  }, []);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ privacy_mode: boolean }>("/health"),
  });
  return (
    <div className={`shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar" inert={collapsed}>
        <Link to="/" className="brand">
          <span className="brand-icon">
            <Network size={23} />
          </span>
          <span>
            ThreatGraph<span className="brand-ai">AI</span>
            <small>DIGITAL TRUST & FRAUD INVESTIGATION</small>
          </span>
        </Link>
        <Link to="/analyze" className="new-investigation">
          <Plus size={18} /> New investigation
        </Link>
        <span className="nav-label">YOUR WORKSPACE</span>
        <nav
          onClick={() => {
            if (window.innerWidth <= 760) setCollapsed(true);
          }}
        >
          {[
            [LayoutDashboard, "Overview", "/dashboard"],
            [ScanLine, "New investigation", "/analyze"],
            [Boxes, "Cases", "/cases"],
            [ScanLine, "Message / email", "/messages"],
            [History, "Analysis history", "/history"],
            [Network, "Intelligence graph", "/intelligence"],
            [Boxes, "Model registry", "/research/models"],
            [BookOpen, "Methodology", "/about/methodology"],
            [ShieldCheck, "Operations", "/admin"],
          ]
            .filter(([, , path]) =>
              path === "/admin"
                ? account.data?.role === "ADMIN"
                : ["/cases", "/intelligence"].includes(String(path))
                  ? ["ADMIN", "ANALYST"].includes(account.data?.role || "")
                  : true,
            )
            .map(([Icon, title, path]: any) => (
              <NavLink key={path} to={path}>
                <Icon size={18} />
                {title}
              </NavLink>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-icon">
            <ShieldCheck size={20} />
          </div>
          <strong>Local by design</strong>
          <p>Files stay in your environment. Evidence stays in your control.</p>
          <span className="status-dot" />
          {health.isError
            ? "API offline"
            : health.data
              ? "API connected"
              : "Connecting"}
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="workspace-title">
            <button
              className="icon-button"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? (
                <PanelLeftOpen size={20} />
              ) : (
                <PanelLeftClose size={20} />
              )}
            </button>
            <span>
              ThreatGraph <strong>Studio</strong>
              <Sparkles size={14} />
            </span>
          </div>
          <CommandMenu />
          <ThemeToggle />
          <span className="local-tag">
            <span className="status-dot" />{" "}
            {health.data?.privacy_mode === false
              ? "External services configurable"
              : "Privacy mode"}
          </span>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Analyze />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/cases/:id" element={<CasePage />} />
            <Route path="/intelligence" element={<Intelligence />} />
            <Route path="/entities/:id" element={<EntityPage />} />
            <Route path="/messages" element={<Message />} />
            <Route path="/admin" element={<Operations />} />
            <Route path="/analysis/:id" element={<Result />} />
            <Route path="/research/models" element={<Models />} />
            <Route path="/about/methodology" element={<Methodology />} />
            <Route
              path="*"
              element={
                <Empty title="Page not found">
                  <Link to="/">Return to investigations</Link>
                </Empty>
              }
            />
          </Routes>
        </main>
        <footer>
          ThreatGraph AI <span>Evidence first. Certainty earned.</span>
          <Link to="/about/methodology">
            Research & limitations <ArrowUpRight size={13} />
          </Link>
        </footer>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <AccountGate>
          <Shell />
        </AccountGate>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
