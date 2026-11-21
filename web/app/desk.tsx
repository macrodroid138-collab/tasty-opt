"use client";

import { useEffect, useMemo, useState } from "react";

type Frame = {
  day: string;
  trader: string;
  clock: string;
  phase: string;
  note: string;
  sig: number;
  ivSource: string;
  pnl: number | null;
  dist?: number;
  anchor?: number;
  price?: number;
  credit?: number;
  cash?: number;
  put?: string;
  call?: string;
  pending?: string | null;
  priorRange?: number;
  priorSkip?: number;
  spyOpen?: number;
  strikes?: { putLong: number; putShort: number; callShort: number; callLong: number };
  tape?: { t: number; quote?: number | null; reject?: string | null; median?: number | null; tradable?: boolean; samples?: number; walk?: { attempt: number; working: number; phase: string; note: string } }[];
};

const DAYS = ["2024-12-18", "2023-01-17", "2022-10-13", "2024-04-04", "2025-04-09"];

export default function Desk() {
  const [trader, setTrader] = useState<"sigma-carry" | "sigma-clip">("sigma-carry");
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [day, setDay] = useState(DAYS[0]);
  const [frames, setFrames] = useState<Frame[]>([]);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tasty, setTasty] = useState("");

  async function load(nextDay = day, nextTrader = trader) {
    setLoading(true);
    setError("");
    setPlaying(false);
    const response = await fetch(`/api/trace?day=${nextDay}&trader=${nextTrader}`);
    const body = await response.json();
    setLoading(false);
    if (!response.ok) {
      setFrames([]);
      setError(body.error || "The session could not be read.");
      return;
    }
    setFrames(body);
    setIndex(0);
  }

  useEffect(() => {
    fetch(`/api/mode?mode=${mode}&trader=${trader}`)
      .then((r) => r.json())
      .then((body) => setTasty(body.message || body.error || ""))
      .catch(() => setTasty("Mode status is unavailable."));
  }, [mode, trader]);

  useEffect(() => {
    if (!playing || frames.length === 0) return;
    const timer = setTimeout(() => {
      setIndex((i) => {
        if (i >= frames.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, 900);
    return () => clearTimeout(timer);
  }, [playing, index, frames.length]);

  const frame = frames[index];
  const tape = frame?.tape || [];
  const ladder = useMemo(() => frame?.strikes, [frame]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[#e2d8c8] pb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#6f675e]">Sigma desk</p>
          <h1 className="text-3xl">{trader === "sigma-carry" ? "Sigma Carry" : "Sigma Clip"}</h1>
          <p className="max-w-xl text-sm text-[#6f675e]">{tasty}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <Toggle on={trader === "sigma-carry"} label="Carry" action={() => { setTrader("sigma-carry"); setFrames([]); }} />
          <Toggle on={trader === "sigma-clip"} label="Clip" action={() => { setTrader("sigma-clip"); setFrames([]); }} />
          <Toggle on={mode === "demo"} label="Demo" action={() => setMode("demo")} />
          <Toggle on={mode === "live"} label="Live" action={() => setMode("live")} />
        </div>
      </header>

      {mode === "live" ? (
        <section className="mt-6 rounded-lg border border-[#e2d8c8] bg-[#fffaf3] p-5">
          <h2 className="text-xl">Live account</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6">
            Live mode signs in to the Tastytrade production API and will send real orders to the account named in
            TASTY_ACCOUNT_NUMBER. It does not start unless TASTY_CLIENT_SECRET and TASTY_REFRESH_TOKEN are set on the server.
            Demo mode is the one that replays a recorded session on this screen. The two programs stay separate: Carry never
            places Clip’s $100 stop, and each keeps its own loss-skip record.
          </p>
        </section>
      ) : (
        <section className="mt-6 flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Session
            <select className="mt-1 block rounded border border-[#e2d8c8] bg-white px-2 py-1" value={day} onChange={(e) => setDay(e.target.value)}>
              {DAYS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <button className="rounded bg-[#1c1915] px-3 py-2 text-sm text-[#f4efe6]" onClick={() => load()} disabled={loading}>
            {loading ? "Reading the path…" : "Load session"}
          </button>
          <button className="rounded border border-[#1c1915] px-3 py-2 text-sm" onClick={() => setPlaying((p) => !p)} disabled={!frames.length}>
            {playing ? "Pause" : "Play"}
          </button>
          <button className="rounded border border-[#e2d8c8] px-3 py-2 text-sm" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={!frames.length}>Back</button>
          <button className="rounded border border-[#e2d8c8] px-3 py-2 text-sm" onClick={() => setIndex((i) => Math.min(frames.length - 1, i + 1))} disabled={!frames.length}>Step</button>
          <span className="text-sm text-[#6f675e]">{frames.length ? `${index + 1} of ${frames.length}` : "No session loaded"}</span>
        </section>
      )}

      {error && <p className="mt-4 text-sm text-[#8f2d2d]">{error}</p>}

      {frame && mode === "demo" && (
        <section className="mt-6 grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
          <article className="rounded-lg border border-[#e2d8c8] bg-[#fffaf3] p-5">
            <div className="flex items-baseline justify-between">
              <p className="text-sm text-[#6f675e]">{frame.day} · {frame.clock}</p>
              <p className="text-sm uppercase tracking-widest text-[#9a5b12]">{frame.phase}</p>
            </div>
            <p className="mt-3 text-2xl leading-snug">{frame.note}</p>
            <dl className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <Stat label="Volatility" value={`${(frame.sig * 100).toFixed(1)}%`} />
              <Stat label="Source" value={frame.ivSource} />
              <Stat label="Distance" value={frame.dist ? `$${frame.dist.toFixed(2)}` : "—"} />
              <Stat label="Anchor" value={frame.anchor?.toFixed(2) ?? "—"} />
              <Stat label="Put wing" value={frame.put ?? "—"} />
              <Stat label="Call wing" value={frame.call ?? "—"} />
              <Stat label="Cash" value={frame.cash != null ? `$${frame.cash.toFixed(0)}` : "—"} />
              <Stat label="Day pnl" value={frame.pnl != null ? `$${frame.pnl.toFixed(0)}` : "open"} />
            </dl>
            {ladder && (
              <div className="mt-5">
                <p className="text-xs uppercase tracking-widest text-[#6f675e]">Strikes</p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  <Pill label="put long" value={ladder.putLong} />
                  <Pill label="put short" value={ladder.putShort} hot />
                  <Pill label="price" value={frame.price ?? frame.anchor ?? 0} />
                  <Pill label="call short" value={ladder.callShort} hot />
                  <Pill label="call long" value={ladder.callLong} />
                </div>
              </div>
            )}
            <p className="mt-4 text-xs text-[#6f675e]">09:30 open ${frame.spyOpen?.toFixed(2)}. Prior session ranged ${frame.priorRange?.toFixed(2)}. A range of ${frame.priorSkip?.toFixed(2)} or more would have skipped the day. Cash and the day result stay in the study's scaled dollars.</p>
          </article>
          <aside className="rounded-lg border border-[#e2d8c8] bg-[#fffaf3] p-5">
            <h2 className="text-lg">Quote tape at the open</h2>
            <p className="mt-1 text-xs leading-5 text-[#6f675e]">Historical option quotes are not in the study. This tape is built around the model credit so you can see a flash get rejected and the median take the fill. The day’s pnl is the backtest number, not this tape.</p>
            <ul className="mt-3 space-y-1 text-sm">
              {tape.map((row, i) => (
                <li key={i} className="flex justify-between gap-3 border-b border-[#e2d8c8] py-1">
                  <span className="text-[#6f675e]">{row.t.toFixed(1)}s</span>
                  <span className={row.reject ? "text-[#8f2d2d]" : ""}>
                    {row.walk ? `walk ${row.walk.attempt}: ${row.walk.note}` : row.reject ? row.reject : `quote ${row.quote?.toFixed(2)} · median ${row.median == null ? "—" : row.median.toFixed(2)}`}
                  </span>
                </li>
              ))}
              {tape.length === 0 && <li className="text-[#6f675e]">No order on this step.</li>}
            </ul>
          </aside>
          <article className="lg:col-span-2 rounded-lg border border-[#e2d8c8] bg-[#fffaf3] p-5">
            <h2 className="text-lg">What the engine has done</h2>
            <ol className="mt-3 max-h-72 space-y-2 overflow-auto text-sm">
              {frames.slice(0, index + 1).map((item, i) => (
                <li key={i} className={i === index ? "text-[#9a5b12]" : ""}>
                  <span className="mr-2 text-[#6f675e]">{item.clock}</span>
                  <span className="mr-2 uppercase">{item.phase}</span>
                  {item.note}
                </li>
              ))}
            </ol>
          </article>
        </section>
      )}
    </main>
  );
}

function Toggle({ on, label, action }: { on: boolean; label: string; action: () => void }) {
  return (
    <button onClick={action} className={`rounded px-3 py-2 ${on ? "bg-[#1c1915] text-[#f4efe6]" : "border border-[#e2d8c8] bg-white"}`}>
      {label}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-widest text-[#6f675e]">{label}</dt>
      <dd className="text-lg">{value}</dd>
    </div>
  );
}

function Pill({ label, value, hot }: { label: string; value: number; hot?: boolean }) {
  return (
    <span className={`rounded px-2 py-1 ${hot ? "bg-[#9a5b12] text-[#fffaf3]" : "bg-[#f4efe6]"}`}>
      {label} {value.toFixed(2)}
    </span>
  );
}
