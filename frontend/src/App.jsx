import { useEffect, useState } from "react";
import { LogOut, MessageCircle, Plus, ShieldCheck, Sparkles } from "lucide-react";

const api = async (path, options = {}) => {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const responseBody = await response.text();
  let data = {};
  if (responseBody) {
    try {
      data = JSON.parse(responseBody);
    } catch {
      data = { detail: responseBody };
    }
  }
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
};

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = await api(`/auth/${mode === "login" ? "login" : "signup"}`, {
        method: "POST", body: JSON.stringify({ email, password })
      });
      localStorage.setItem("local-ai-token", session.token);
      onAuthenticated(session.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-shell">
    <section className="auth-art">
      <div className="brand-mark"><Sparkles size={18} /> LOCAL / AI</div>
      <div className="art-copy">
        <p className="eyebrow">Private by default</p>
        <h1>A quieter way to think with code.</h1>
        <p>Ask questions, explore ideas, and keep your work close to home.</p>
      </div>
      <div className="art-foot"><ShieldCheck size={16} /> Your chat is protected by your account</div>
    </section>
    <section className="auth-panel">
      <div className="auth-heading"><MessageCircle size={22} /><span>{mode === "login" ? "Welcome back" : "Create your workspace"}</span></div>
      <p className="muted">{mode === "login" ? "Sign in to continue your conversation." : "Set up an account to use the AI chat."}</p>
      <form onSubmit={submit}>
        <label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" required /></label>
        <label>Password<input type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters" minLength="8" required /></label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}</button>
      </form>
      <button className="link-button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
        {mode === "login" ? "Need an account? Sign up" : "Already have an account? Sign in"}
      </button>
    </section>
  </main>;
}

function ChatScreen({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/chat/history", { headers: { Authorization: `Bearer ${localStorage.getItem("local-ai-token")}` } })
      .then(data => setMessages(data.messages))
      .catch(() => setMessages([]));
  }, []);

  async function send(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const result = await api("/chat", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("local-ai-token")}` },
        body: JSON.stringify({ messages: next })
      });
      setMessages([...next, result.message]);
    } catch (error) {
      setMessages([...next, { role: "assistant", content: error.message }]);
    } finally { setBusy(false); }
  }

  async function logout() {
    await api("/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("local-ai-token")}` } });
    localStorage.removeItem("local-ai-token");
    onLogout();
  }

  function startNewChat() {
    setMessages([]);
    setInput("");
  }

  return <main className="chat-shell">
    <header className="topbar"><div className="brand-mark"><Sparkles size={18} /> LOCAL / AI</div><div className="account"><button className="new-chat" title="Start a new chat" onClick={startNewChat}><Plus size={17} /><span>New chat</span></button><span>{user.email}</span><button title="Sign out" onClick={logout}><LogOut size={17} /></button></div></header>
    <section className="conversation">
      {messages.length === 0 ? <div className="empty-state"><div className="empty-icon"><Sparkles size={24} /></div><p className="eyebrow">Private AI workspace</p><h1>What are you working through?</h1><p className="muted">Ask a question, explore a concept, or get a second perspective.</p></div> : messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><span className="message-label">{message.role === "user" ? "YOU" : "AI"}</span><p>{message.content}</p></article>)}
      {busy && <div className="thinking"><span></span><span></span><span></span> thinking</div>}
    </section>
    <form className="composer" onSubmit={send}><textarea value={input} onChange={event => setInput(event.target.value)} placeholder="Ask anything..." rows="1" /><button className="primary" disabled={busy || !input.trim()}>Send</button></form>
  </main>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { const token = localStorage.getItem("local-ai-token"); if (!token) return setLoading(false); api("/auth/me", { headers: { Authorization: `Bearer ${token}` } }).then(data => setUser(data.user)).catch(() => localStorage.removeItem("local-ai-token")).finally(() => setLoading(false)); }, []);
  if (loading) return <div className="loading">Loading workspace...</div>;
  return user ? <ChatScreen user={user} onLogout={() => setUser(null)} /> : <AuthScreen onAuthenticated={setUser} />;
}
