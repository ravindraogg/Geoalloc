'use client';
import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';

const GlobeGl = dynamic(() => import('react-globe.gl'), { ssr: false });

// --- Types adapted for GeoAlloc ---
interface CountryNode {
  id: string;
  lat: number;
  lng: number;
  stability: number;
  demand: number;
  received: number;
  enemies: string[];
}

// --- Visual Components ---
function ScanlineOverlay() {
  return (
    <div
      className="absolute inset-0 pointer-events-none z-10"
      style={{
        backgroundImage:
          'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,242,255,0.015) 2px, rgba(0,242,255,0.015) 4px)',
        mixBlendMode: 'screen',
      }}
    />
  );
}

function GridOverlay() {
  return (
    <div
      className="absolute inset-0 pointer-events-none z-10"
      style={{
        backgroundImage:
          'linear-gradient(rgba(0,242,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,242,255,0.04) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }}
    />
  );
}

export default function Globe({ data }: { data: any[] }) {
  const globeRef = useRef<any>(null);

  useEffect(() => {
    if (globeRef.current && data.length > 0) {
      const focusedPoint = data.find((p: any) => p.opacity === 1 && p.size === 1.0);
      
      if (focusedPoint) {
        // Zoom into focused country
        globeRef.current.pointOfView({ lat: focusedPoint.lat, lng: focusedPoint.lng, altitude: 1.5 }, 1000);
      } else {
        // Global overview
        globeRef.current.pointOfView({ altitude: 2.5 }, 1000);
      }
    }
  }, [data]);

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-3xl overflow-hidden glass border border-white/5">
      <ScanlineOverlay />
      <GridOverlay />
      
      <div className="absolute inset-0 z-0 flex items-center justify-center">
        <GlobeGl
          ref={globeRef}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          backgroundColor="rgba(0,0,0,0)"
          atmosphereColor="rgba(0,242,255,0.2)"
          atmosphereAltitude={0.15}
          pointsData={data}
          pointLat="lat"
          pointLng="lng"
          pointColor={(d: any) => d.color}
          pointRadius="size"
          pointAltitude={0.02}
          pointsMerge={false}
          pointLabel={(d: any) => `
            <div class="glass p-4 rounded-2xl border border-white/10 text-[10px] font-mono min-w-[150px]">
              <div class="font-black text-cyan-400 uppercase tracking-[0.2em] mb-2">${d.id}</div>
              <div class="space-y-1">
                <div class="flex justify-between">
                  <span class="text-white/40 uppercase">Stability</span>
                  <span class="${d.stability < 0.4 ? 'text-red-500' : 'text-white'}">${Math.round(d.stability * 100)}%</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-white/40 uppercase">Demand</span>
                  <span class="text-white">${Math.round(d.demand)}u</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-white/40 uppercase">Met</span>
                  <span class="text-cyan-400">${Math.round(d.received)}u</span>
                </div>
              </div>
            </div>
          `}
        />
      </div>

      {/* Radar Overlay */}
      <div className="absolute top-6 left-6 z-20 flex items-center gap-3">
        <div className="relative w-3 h-3">
          <div className="absolute inset-0 bg-cyan-500 rounded-full animate-ping" />
          <div className="relative w-full h-full bg-cyan-500 rounded-full" />
        </div>
        <span className="text-[10px] font-black font-mono tracking-[0.3em] text-cyan-400 uppercase">
          Live Strategic Vector
        </span>
      </div>

      {/* Controls Hint */}
      <div className="absolute bottom-6 left-6 z-20 pointer-events-none">
        <div className="flex gap-4 text-[8px] font-mono text-white/20 tracking-widest uppercase">
          <span>Drag to Rotate</span>
          <span className="w-px h-3 bg-white/10" />
          <span>Scroll to Zoom</span>
        </div>
      </div>
    </div>
  );
}
