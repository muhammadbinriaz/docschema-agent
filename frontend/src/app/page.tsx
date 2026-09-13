"use client";

import { useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8001/api/v1";

const SAMPLE = `INVOICE
From: Northstar Billing
Vendor email: billing@northstar.example
Invoice # INV-2026-0842
Date: 2026-08-15
Due date: 2026-09-14

Bill to: Maya Chen
Customer email: maya.chen@orbitly.io
Company: Orbitly Inc.

Line items:
- Northstar Annual Plan                    $249.00
- Onboarding workshop (waived)               $0.00

Subtotal: $249.00
Tax: $0.00
Total due: $249.00
Currency: USD

Payment terms: Net 30. Refunds follow Northstar Refund Policy (30-day window).
Notes: Order reference #4821.
`;

type Field = {
  value: unknown;
  confidence: number;
  uncertain: boolean;
  edited?: boolean;
};

type Job = {
  id: string;
  filename: string | null;
  doc_type: string | null;
  status: string;
  fields: Record<string, Field>;
  error: string | null;
};

export default function Home() {
  const [text, setText] = useState(SAMPLE);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const entries = useMemo(() => Object.entries(job?.fields ?? {}), [job]);

  async function extract() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, filename: "invoice-orbitly.txt", schema_name: "invoice" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: Job = await res.json();
      setJob(data);
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(data.fields || {})) {
        next[k] = v.value == null ? "" : String(v.value);
      }
      setDrafts(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Extract failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveField(key: string) {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/jobs/${job.id}/fields/${key}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: drafts[key] ?? "" }),
      });
      if (!res.ok) throw new Error(await res.text());
      setJob(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!job) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/jobs/${job.id}/confirm`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      setJob(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }

  function exportUrl(format: "json" | "csv") {
    if (!job) return "#";
    return `${API}/jobs/${job.id}/export?format=${format}`;
  }

  return (
    <div className="wrap">
      <header className="nav">
        <div className="brand">
          <span />
          DocSchema
        </div>
        <a href="https://github.com/muhammadbinriaz" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </header>

      <section className="hero">
        <h1>
          Documents in. <em>Structured fields</em> out.
        </h1>
        <p>
          Extract invoice fields, flag uncertain cells, edit, then export JSON or CSV —
          the sister product to ActionGate&apos;s HITL ops loop.
        </p>
      </section>

      <section className="panel">
        <h2>1. Source document</h2>
        <p className="muted">Paste text or load the sample Orbitly invoice.</p>
        <textarea value={text} onChange={(e) => setText(e.target.value)} />
        <div className="row">
          <button type="button" className="btn btn-ghost" onClick={() => setText(SAMPLE)}>
            Load sample
          </button>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={extract}>
            {busy ? "Extracting…" : "Extract fields"}
          </button>
        </div>
        {error && <p className="err">{error}</p>}
      </section>

      {job && (
        <section className="panel">
          <h2>2. Review table</h2>
          <p className="status">
            Job <code>{job.id.slice(0, 8)}</code> · {job.doc_type || "unknown"} ·{" "}
            <strong>{job.status}</strong>
            {job.error ? ` · ${job.error}` : ""}
          </p>
          <table>
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
                <th>Confidence</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([key, field]) => (
                <tr key={key}>
                  <td>
                    <code>{key}</code>
                  </td>
                  <td>
                    <input
                      className="field"
                      value={drafts[key] ?? ""}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [key]: e.target.value,
                        }))
                      }
                    />
                  </td>
                  <td>
                    {field.edited ? (
                      <span className="chip chip-edit">edited</span>
                    ) : field.uncertain ? (
                      <span className="chip chip-warn">
                        uncertain {(field.confidence * 100).toFixed(0)}%
                      </span>
                    ) : (
                      <span className="chip chip-ok">
                        {(field.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busy}
                      onClick={() => saveField(key)}
                    >
                      Save
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            <button type="button" className="btn btn-primary" disabled={busy} onClick={confirm}>
              Mark confirmed
            </button>
            <a className="btn btn-ghost" href={exportUrl("json")} target="_blank" rel="noreferrer">
              Export JSON
            </a>
            <a className="btn btn-ghost" href={exportUrl("csv")} target="_blank" rel="noreferrer">
              Export CSV
            </a>
          </div>
        </section>
      )}
    </div>
  );
}
