"use client";

import Image from "next/image";
import React, { useState, useEffect, useMemo } from "react";
import Globe from "../components/Globe";
import countryDataRaw from "./data/countries.json";

// --- Types ---
interface Country {
  id: string;
  demand: number;
  received: number;
  stability: number;
  allies: string[];
  enemies: string[];
  unmet_demand: number;
  refinery_capacity: number;
  refined_buffer: number;
}

interface Projection {
  stability_delta: number;
  tension_delta: number;
}

interface Observation {
  available_oil: number;
  countries: Country[];
  global_tension: number;
  time_step: number;
  max_steps: number;
  done: boolean;
  reward: number;
  projection?: {
    allocate: Projection;
    no_op: Projection;
  };
}

const geoAllocCoords: Record<string, [number, number]> = {
  "ares": [38.0, 23.0],
  "zeus": [40.0, 22.0],
  "hera": [36.0, 24.0],
  "poseidon": [30.0, -30.0],
  "athena": [38.0, 20.0]
};

const countryCoords = { ...countryDataRaw, ...geoAllocCoords } as unknown as Record<string, [number, number]>;

// --- Components ---

const TensionGauge = ({ value }: { value: number }) => {
  const percentage = Math.min(Math.max(value * 100, 0), 100);
  let colorClass = "from-cyan-400 to-blue-500";
  if (value > 0.5) colorClass = "from-amber-400 to-orange-500";
  if (value > 0.8) colorClass = "from-red-500 to-red-600";

  return (
    <div className="relative w-full h-4 bg-white/5 rounded-full overflow-hidden glass border border-white/10">
      <div
        className={`absolute top-0 left-0 h-full bg-gradient-to-r transition-all duration-700 ease-out ${colorClass}`}
        style={{ width: `${percentage}%` }}
      />
      {value > 0.8 && <div className="absolute top-0 left-0 h-full w-full animate-pulse bg-red-500/20" />}
    </div>
  );
};

const CountryCard = ({ country, onFocus }: { country: Country, onFocus: (id: string) => void }) => {
  const supplyPercentage = country.demand > 0 ? (country.received / country.demand) * 100 : 100;
  const stabilityPercentage = country.stability * 100;

  return (
    <div 
      onClick={() => onFocus(country.id)}
      className="glass p-5 rounded-2xl flex flex-col gap-4 border border-white/5 hover:border-cyan-500/30 transition-all group cursor-pointer relative overflow-hidden"
    >
      <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex justify-between items-start relative z-10">
        <div>
          <h3 className="text-xl font-bold uppercase tracking-wider text-white/90 group-hover:text-cyan-400 transition-colors">
            {country.id}
          </h3>
          <div className="flex flex-wrap gap-2 mt-1">
            {country.enemies.slice(0, 1).map(e => (
              <span key={e} className="text-[8px] bg-red-500/10 text-red-400 px-2 py-0.5 rounded border border-red-500/20 uppercase font-bold">
                Conflict: {e}
              </span>
            ))}
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-white/40 block uppercase tracking-widest font-bold">Demand</span>
          <span className="text-lg font-mono font-bold text-white/80">{Math.round(country.demand)}u</span>
        </div>
      </div>

      <div className="space-y-3 relative z-10">
        <div className="space-y-1">
          <div className="flex justify-between text-[8px] uppercase tracking-widest text-white/40 font-black">
            <span>Supply</span>
            <span className={supplyPercentage >= 100 ? "text-cyan-400" : ""}>{Math.round(supplyPercentage)}%</span>
          </div>
          <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-400 transition-all duration-500 shadow-[0_0_8px_rgba(34,211,238,0.5)]"
              style={{ width: `${Math.min(supplyPercentage, 100)}%` }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[8px] uppercase tracking-widest text-white/40 font-black">
            <span>Stability</span>
            <span>{Math.round(stabilityPercentage)}%</span>
          </div>
          <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-500 via-amber-400 to-green-500 transition-all duration-1000"
              style={{ width: `${stabilityPercentage}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

const FocusedView = ({ country, allCountries, globalTension, projection, onAllocate, onWait }: { 
  country: Country, 
  allCountries: Country[], 
  globalTension: number,
  projection?: Observation['projection'],
  onAllocate: (amount: number) => void,
  onWait: () => void 
}) => {
  const [amount, setAmount] = useState(25);
  
  const allies = allCountries.filter(c => country.allies.includes(c.id));
  const enemies = allCountries.filter(c => country.enemies.includes(c.id));
  const isHighTension = globalTension > 0.6;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Decision Insight Panel */}
        <div className={`p-6 rounded-3xl border flex flex-col justify-between glass ${isHighTension ? 'border-red-500/30 bg-red-500/5' : 'border-cyan-500/30 bg-cyan-500/5'}`}>
          <div className="flex items-center gap-4 mb-4">
            <div className={`w-2 h-2 rounded-full animate-pulse ${isHighTension ? 'bg-red-500' : 'bg-cyan-500'}`} />
            <h3 className="text-[10px] font-black uppercase tracking-widest text-white/60">Strategic Foresight</h3>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-white/80">{isHighTension ? "⚠️ High Tension: Restraint Advised" : "✅ Low Tension: Safe to Act"}</span>
              <span className="text-[10px] font-mono text-white/20 uppercase">Confidence: 0.94</span>
            </div>
            {projection && (
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5">
                <div className="space-y-1">
                  <span className="text-[8px] uppercase text-white/30 font-bold">If Allocate</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-green-400 font-mono">+{projection.allocate.stability_delta.toFixed(3)}s</span>
                    <span className="text-[10px] text-red-400 font-mono">+{projection.allocate.tension_delta.toFixed(3)}t</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-[8px] uppercase text-white/30 font-bold">If Wait</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-white/60 font-mono">+{projection.no_op.stability_delta.toFixed(3)}s</span>
                    <span className="text-[10px] text-cyan-400 font-mono">{projection.no_op.tension_delta.toFixed(3)}t</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Refinery Insight Panel */}
        <div className="glass p-6 rounded-3xl border-white/5 flex flex-col justify-between">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-2 h-2 rounded-full bg-amber-500/50" />
            <h3 className="text-[10px] font-black uppercase tracking-widest text-white/60">Refinery Systems</h3>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-1">
              <span className="text-[8px] text-white/30 uppercase font-bold block">Capacity</span>
              <span className="text-xl font-mono font-bold text-amber-400">{Math.round(country.refinery_capacity * 100)}%</span>
            </div>
            <div className="space-y-1">
              <span className="text-[8px] text-white/30 uppercase font-bold block">In Pipeline</span>
              <span className="text-xl font-mono font-bold text-cyan-400">{Math.round(country.refined_buffer)}u</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Core Stats */}
        <div className="md:col-span-2 glass p-8 rounded-3xl space-y-8 relative overflow-hidden border-white/5">
          <div className="relative z-10">
            <h2 className="text-4xl font-black uppercase tracking-tighter mb-2">{country.id}</h2>
            <div className="flex gap-4 items-center">
              <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${country.stability > 0.7 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                Status: {country.stability > 0.7 ? 'Stable' : 'Unstable'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-8 relative z-10">
            <div className="space-y-1">
              <span className="text-[10px] text-white/30 uppercase block font-bold">Unmet Demand</span>
              <span className="text-2xl font-mono font-bold text-red-400">{Math.round(country.unmet_demand)}u</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-white/30 uppercase block font-bold">Received</span>
              <span className="text-2xl font-mono font-bold text-cyan-400">{Math.round(country.received)}u</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-white/30 uppercase block font-bold">Stability</span>
              <span className="text-2xl font-mono font-bold">{Math.round(country.stability * 100)}%</span>
            </div>
          </div>
        </div>

        {/* Action Panel */}
        <div className="glass p-8 rounded-3xl border-white/10 flex flex-col justify-between bg-gradient-to-br from-white/5 to-transparent">
          <div className="space-y-6">
            <h3 className="text-xs font-black text-cyan-400 uppercase tracking-widest">Decision Matrix</h3>
            <div className="space-y-4">
              <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-white/40">
                <span>Alloc Amount</span>
                <span className="text-cyan-400">{amount} units</span>
              </div>
              <input 
                type="range" min="0" max="100" value={amount} 
                onChange={(e) => setAmount(parseInt(e.target.value))}
                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyan-500"
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <button 
              onClick={() => onAllocate(amount)}
              className="w-full py-4 rounded-2xl bg-cyan-500 text-black font-black uppercase tracking-widest hover:bg-cyan-400 transition-all shadow-[0_0_20px_rgba(34,211,238,0.3)]"
            >
              Confirm Allocation
            </button>
            <button 
              onClick={() => onWait()}
              className="w-full py-3 rounded-xl bg-white/5 text-white/60 text-[10px] font-black uppercase tracking-widest hover:bg-white/10 hover:text-white transition-all"
            >
              Strategic Hold (No-Op)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_NEXT_API_URI || "http://localhost:8000";

export default function Home() {
  const [obs, setObs] = useState<Observation | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const addLog = (msg: string) => {
    setLogs(prev => [msg, ...prev].slice(0, 50));
  };

  useEffect(() => {
    console.log(`[Neural Link] Connecting to Strategic Hub at: ${BACKEND_URL}`);
  }, []);

  const fetchData = async (action?: any) => {
    setLoading(true);
    try {
      const isReset = !action;
      const endpoint = isReset ? "reset" : "step";
      addLog(`${isReset ? "Resetting Environment..." : `Executing Strategic Action...`}`);

      const response = await fetch(`${BACKEND_URL}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isReset ? { params: {} } : { action: action })
      });

      if (!response.ok) throw new Error("Backend unreachable");

      const data = await response.json();
      const observation = data.observation || data;
      setObs(observation);

      if (!isReset) {
        addLog(`Strategic Update: Global Tension at ${observation.global_tension.toFixed(3)}.`);
        if (action.type === 'no_op') {
          addLog("Reasoning Trace: Selecting NO_OP to facilitate tension decay.");
        } else {
          addLog(`Reasoning Trace: Allocated ${action.amount} units to ${action.country_id}.`);
        }
      }
    } catch (e) {
      addLog("CRITICAL ERROR: Neural Link severed.");
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const topUnstable = useMemo(() => {
    if (!obs) return [];
    return [...obs.countries].sort((a, b) => a.stability - b.stability).slice(0, 6);
  }, [obs]);

  const focusedCountry = useMemo(() => {
    if (!obs || filter === "all") return null;
    return obs.countries.find(c => c.id.toLowerCase() === filter.toLowerCase());
  }, [obs, filter]);

  const globePoints = useMemo(() => {
    if (!obs) return [];
    const focusedId = filter.toLowerCase();
    const focusedCountry = obs.countries.find(c => c.id.toLowerCase() === focusedId);
    
    return obs.countries.map(c => {
      const coords = countryCoords[c.id];
      if (!coords) return null;
      
      const isFocused = filter !== "all" && c.id.toLowerCase() === focusedId;
      const isEnemy = focusedCountry?.enemies.includes(c.id);
      
      // Determine behavior based on mode
      let size = 0.1 + (1 - c.stability) * 0.4;
      let color = c.stability < 0.4 ? "#ef4444" : c.stability < 0.7 ? "#fbbf24" : "#22d3ee";
      let opacity = 1;

      if (filter !== "all") {
        if (isFocused) {
          size = 1.0;
          color = "#00f2ff"; // Bright Cyan
        } else if (isEnemy) {
          size = 0.6;
          color = "#ff0000"; // Sharp Red
        } else {
          size = 0.05;
          opacity = 0.2; // Dimmed
          color = "#ffffff";
        }
      }

      return {
        ...c,
        lat: coords[0],
        lng: coords[1],
        size,
        color,
        opacity
      };
    }).filter(p => p !== null);
  }, [obs, filter]);

  if (!obs) return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <span className="text-cyan-500 font-mono text-[10px] uppercase tracking-[0.5em] animate-pulse">Initializing Neural Link</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans selection:bg-cyan-500/30 relative overflow-hidden">
      <div className="absolute inset-0 grid-pattern pointer-events-none z-0 opacity-20" />
      <div className="absolute inset-0 scanlines pointer-events-none z-10 opacity-30" />

      <div className="relative z-20 p-6 md:p-10">
        <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center mb-12 gap-6">
          <div className="space-y-1">
            <h1 className="text-4xl font-black tracking-tighter bg-gradient-to-r from-white to-white/40 bg-clip-text text-transparent uppercase">
              GeoAlloc <span className="text-cyan-400">Env</span>
            </h1>
            <p className="text-[10px] text-white/40 tracking-[0.3em] uppercase font-bold">Global Equilibrium Monitoring System • 2026</p>
          </div>

          <div className="flex items-center gap-8 glass px-10 py-5 rounded-[2rem] border-white/5 bg-white/5">
            <div className="text-center">
              <span className="text-[9px] text-white/20 uppercase block mb-1 font-black">Time Step</span>
              <span className="text-2xl font-mono font-bold text-cyan-400">{obs.time_step}<span className="text-white/20 mx-1">/</span>{obs.max_steps}</span>
            </div>
            <div className="w-px h-10 bg-white/5" />
            <div className="text-center">
              <span className="text-[9px] text-white/20 uppercase block mb-1 font-black">Reserve</span>
              <span className="text-2xl font-mono font-bold">{Math.round(obs.available_oil)}<span className="text-[10px] text-white/40 ml-1">u</span></span>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto flex flex-col gap-10">
          <div className="flex flex-col md:flex-row justify-between items-end gap-6 border-b border-white/5 pb-8">
            <div className="space-y-2">
              <h2 className="text-[10px] font-black text-cyan-400 uppercase tracking-[0.5em]">{filter === 'all' ? 'Global Command Center' : `Sector Intelligence: ${filter}`}</h2>
              <div className="flex items-center gap-4">
                <div className="h-1 w-24 bg-cyan-500/50 rounded-full" />
                <span className="text-[10px] text-white/20 font-mono tracking-widest animate-pulse uppercase">Active Stream</span>
              </div>
            </div>
            
            <div className="relative group min-w-[280px]">
              <span className="absolute -top-2 left-4 px-2 bg-[#050505] text-[8px] text-cyan-500 font-black uppercase tracking-widest z-10 border border-white/5 rounded-full">Select Strategic Sector</span>
              <select 
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-white/5 border border-white/10 text-white text-[10px] uppercase tracking-[0.2em] font-black py-4 px-8 rounded-2xl focus:outline-none focus:border-cyan-500/50 appearance-none cursor-pointer hover:bg-white/10 transition-all w-full glass"
              >
                <option value="all" className="bg-[#050505]">All Regions (Overview)</option>
                {Object.keys(countryCoords).sort().map(name => (
                  <option key={name} value={name} className="bg-[#050505]">{name}</option>
                ))}
              </select>
              <div className="absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-cyan-500/50">
                <svg width="12" height="10" viewBox="0 0 12 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 3L6 7L10 3" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
            <div className="xl:col-span-8 space-y-10">
              {/* Main Globe Area */}
              <section className="h-[650px] w-full rounded-[2.5rem] overflow-hidden glass border border-white/5 shadow-[0_0_80px_rgba(0,0,0,0.5)] relative group">
                <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 to-transparent pointer-events-none z-10" />
                <Globe data={globePoints} />
                <div className="absolute bottom-8 right-8 glass px-6 py-4 rounded-2xl border border-white/5 z-20 bg-[#050505]/40">
                  <div className="flex items-center gap-6 text-[9px] uppercase tracking-[0.2em] font-black">
                    <div className="flex items-center gap-2 text-cyan-400"><div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" /> Nominal</div>
                    <div className="flex items-center gap-2 text-amber-400"><div className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" /> Caution</div>
                    <div className="flex items-center gap-2 text-red-500"><div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" /> Critical</div>
                  </div>
                </div>
              </section>

              {/* Dynamic Content: Focus vs Overview */}
              {focusedCountry ? (
                <FocusedView 
                  country={focusedCountry} 
                  allCountries={obs.countries}
                  globalTension={obs.global_tension}
                  projection={obs.projection}
                  onAllocate={(amt) => fetchData({ type: 'allocate', country_id: focusedCountry.id, amount: amt })} 
                  onWait={() => fetchData({ type: 'no_op' })}
                />
              ) : (
                <div className="space-y-10">
                  <section className="glass p-10 rounded-[2.5rem] space-y-8 relative overflow-hidden border-white/5">
                    <div className="flex justify-between items-end">
                      <div className="space-y-1">
                        <h2 className="text-xs font-black text-white/30 uppercase tracking-[0.3em]">Global Stability Pressure</h2>
                        <p className="text-[10px] text-white/10 italic font-mono uppercase">System Capacity: 1.000 MAX</p>
                      </div>
                      <span className={`text-6xl font-black font-mono tracking-tighter ${(obs.global_tension > 0.8) ? 'text-red-500' : 'text-white'}`}>
                        {obs.global_tension.toFixed(3)}
                      </span>
                    </div>
                    {obs.global_tension > 0.6 && (
                      <div className="flex items-center gap-3 bg-cyan-500/10 border border-cyan-500/20 p-3 rounded-xl animate-in fade-in zoom-in duration-500">
                        <div className="w-2 h-2 rounded-full bg-cyan-500 animate-ping" />
                        <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">
                          Protocol: Strategic Restraint Active
                        </span>
                      </div>
                    )}
                    <TensionGauge value={obs.global_tension} />
                  </section>

                  <section className="space-y-6">
                    <div className="flex items-center gap-4">
                      <h3 className="text-[10px] font-black text-cyan-400/60 uppercase tracking-[0.5em]">High-Risk Vectors</h3>
                      <div className="h-px flex-1 bg-white/5" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {topUnstable.map(c => (
                        <CountryCard key={c.id} country={c} onFocus={setFilter} />
                      ))}
                    </div>
                  </section>
                </div>
              )}
            </div>

            <div className="xl:col-span-4 flex flex-col gap-8 h-full">
              {/* Global Controls */}
              <section className="glass p-8 rounded-[2.5rem] space-y-6 border-white/5">
                <h2 className="text-[10px] font-black text-white/30 uppercase tracking-[0.3em]">Command Protocols</h2>
                <div className="grid grid-cols-1 gap-3">
                  <button
                    onClick={() => fetchData({ type: 'no_op' })}
                    disabled={loading}
                    className="py-5 px-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all text-[10px] font-black uppercase tracking-[0.3em] disabled:opacity-50 text-white/60 hover:text-white"
                  >
                    Strategic Hold
                  </button>
                  <button
                    onClick={() => fetchData()}
                    disabled={loading}
                    className="py-5 px-4 rounded-2xl bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 transition-all text-[10px] font-black uppercase tracking-[0.3em] disabled:opacity-50 text-red-500/60 hover:text-red-500"
                  >
                    System Reset
                  </button>
                </div>
              </section>

              {/* Real-time Logs */}
              <section className="glass rounded-[2.5rem] flex-1 flex flex-col overflow-hidden min-h-[500px] border-white/5">
                <div className="p-8 border-b border-white/5 flex justify-between items-center bg-white/2 shadow-inner">
                  <h2 className="text-[10px] font-black text-white/30 uppercase tracking-[0.3em]">Intelligence Feed</h2>
                  <div className="flex gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500/20" />
                  </div>
                </div>
                <div className="flex-1 p-8 font-mono text-[10px] leading-relaxed space-y-6 overflow-y-auto max-h-[600px] scrollbar-thin scrollbar-thumb-white/5 hover:scrollbar-thumb-white/10 transition-all">
                  {logs.length === 0 && <span className="text-white/10 uppercase tracking-widest font-black flex items-center justify-center h-full">Initializing Feed...</span>}
                  {logs.map((log, i) => (
                    <div key={i} className={`${i === 0 ? "text-cyan-400" : "text-white/30"} border-l border-current pl-6 relative group/log`}>
                      <div className={`absolute left-[-2px] top-0 w-1 h-1 rounded-full ${i === 0 ? "bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,1)]" : "bg-white/10"}`} />
                      <span className="opacity-40 text-[8px] block mb-1">[{new Date().toLocaleTimeString()}]</span>
                      <span className="group-hover/log:text-white/60 transition-colors">{log}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </main>

        <footer className="max-w-7xl mx-auto mt-16 pt-10 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6 text-[9px] text-white/20 uppercase tracking-[0.4em] font-black">
          <div className="flex gap-10">
            <span className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-green-500" /> System: Nominal</span>
            <span>Latency: 24ms</span>
          </div>
          <span className="text-white/10">GeoAlloc Quantum-Resistant Grid • v2.1.0-PRO</span>
        </footer>
      </div>
    </div>
  );
}

