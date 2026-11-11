import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import React from "react";
import WorkspaceNavigation from "./components/WorkspaceNavigation";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { api } from "./api";
import "@fontsource-variable/manrope";
import "@fontsource-variable/inter";
import "./styles.css";
import "./studio.css";
import "./theme.css";
import "./cases.css";
import "./product.css";
import "./experience.css";
import "./visual-studio.css";
import "./navigation.css";
import "./auth.css";
import Demo from "./pages/Demo";

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

function Shell() {
  const account = useQuery({
    queryKey: ["account"],
    queryFn: () => api<{ role: string; email?:string; auth_required:boolean }>("/auth/me"),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ privacy_mode: boolean }>("/health"),
  });
  return (
    <div className="navigation-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <WorkspaceNavigation role={account.data?.role} connected={!!health.data} offline={health.isError} privacy={health.data?.privacy_mode} email={account.data?.email} authRequired={account.data?.auth_required}/>
      <div className="workspace">
        <main id="main-content" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Analyze />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/demo" element={<Demo />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/cases/:id" element={<CasePage />} />
            <Route path="/intelligence" element={<Intelligence />} />
            <Route path="/entities/:id" element={<EntityPage />} />
            <Route path="/messages" element={<Message />} />

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
