"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    setAnswer("");
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, company_code: "LOCKTON" }),
    });
    const data = await res.json();
    setAnswer(data.answer || JSON.stringify(data));
    setLoading(false);
  }

  async function addUrl() {
    setLoading(true);
    const res = await fetch(`${API_BASE}/api/sources/url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, company_code: "LOCKTON", run_deep_enrichment: true }),
    });
    const data = await res.json();
    setJob(data);
    setLoading(false);
  }

  return (
    <main className="min-h-screen p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm">
          <h1 className="text-3xl font-bold">Enterprise LLM Wiki</h1>
          <p className="mt-2 text-slate-600">Chatbot + LLM Wiki + Knowledge Pipeline</p>
        </header>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Add URL</h2>
            <input className="mt-4 w-full rounded-xl border p-3" placeholder="https://example.com/page" value={url} onChange={(e) => setUrl(e.target.value)} />
            <button onClick={addUrl} disabled={loading || !url} className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-white disabled:opacity-50">Create Ingest Job</button>
            {job && <pre className="mt-4 rounded-xl bg-slate-100 p-3 text-sm">{JSON.stringify(job, null, 2)}</pre>}
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Chat Test</h2>
            <textarea className="mt-4 h-28 w-full rounded-xl border p-3" placeholder="ถามคำถาม..." value={question} onChange={(e) => setQuestion(e.target.value)} />
            <button onClick={ask} disabled={loading || !question} className="mt-3 rounded-xl bg-blue-700 px-4 py-2 text-white disabled:opacity-50">Ask</button>
            {answer && <div className="mt-4 whitespace-pre-wrap rounded-xl bg-slate-100 p-4">{answer}</div>}
          </div>
        </section>
      </div>
    </main>
  );
}
