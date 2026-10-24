import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { api } from "../api";
import { ErrorBox, Loading, client } from "./shared";
export default function AccountGate({ children }: { children: ReactNode }) {
  const me = useQuery({
    queryKey: ["account"],
    queryFn: () =>
      api<{ auth_required: boolean; email?: string; role: string }>("/auth/me"),
    retry: false,
  });
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [register, setRegister] = useState(false),
    [error, setError] = useState<Error | null>(null),
    [busy, setBusy] = useState(false);
  const [extensionToken, setExtensionToken] = useState("");
  const [extensionError, setExtensionError] = useState("");
  if (me.isPending) return <Loading />;
  if (me.data)
    return (
      <>
        {me.data.auth_required && (
          <div className="case-actions account-bar">
            <span>
              {me.data.email} · {me.data.role}
            </span>
            <button
              onClick={async () => {
                setExtensionError("");
                try {
                  const result = await api<{ token: string }>("/auth/token", {
                    method: "POST",
                  });
                  setExtensionToken(result.token);
                } catch (e) {
                  setExtensionError((e as Error).message);
                }
              }}
            >
              Create extension token
            </button>
            {extensionError && <span role="alert">{extensionError}</span>}
            {extensionToken && (
              <label>
                Private token (expires in 12 hours)
                <input
                  readOnly
                  type="password"
                  value={extensionToken}
                  onFocus={(e) => e.currentTarget.select()}
                />
                <button onClick={() => setExtensionToken("")}>
                  Hide token
                </button>
              </label>
            )}
            <button
              onClick={async () => {
                await api("/auth/logout", { method: "POST" });
                client.clear();
                window.location.assign("/");
              }}
            >
              Sign out & revoke tokens
            </button>
          </div>
        )}
        {children}
      </>
    );
  return (
    <main className="account-login">
      <h1>ThreatGraph AI</h1>
      <p>Sign in to your investigation workspace.</p>
      <form
        className="card case-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            const options = {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email, password }),
            };
            if (register) await api("/auth/register", options);
            await api("/auth/login", options);
            setPassword("");
            await client.invalidateQueries({ queryKey: ["account"] });
          } catch (e) {
            setError(e as Error);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          Password (at least 12 characters)
          <input
            type="password"
            minLength={12}
            maxLength={256}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={register ? "new-password" : "current-password"}
          />
        </label>
        <button disabled={busy}>
          {register ? "Create account" : "Sign in"}
        </button>
        <button type="button" onClick={() => setRegister(!register)}>
          {register ? "Use existing account" : "Create an account"}
        </button>
        {error && <ErrorBox error={error} />}
      </form>
    </main>
  );
}
