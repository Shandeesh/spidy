import React, { useState } from 'react';
import { Shield, TrendingUp, TrendingDown, DollarSign, Activity, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ShoongaControlPanel() {
    return (
        <div className="flex flex-col gap-4">
            {/* PCR SIGNAL BOX (Phase 3 Placeholder) */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5 shadow-lg relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <Activity size={48} />
                </div>

                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Market PCR</h3>
                    <span className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded border border-green-500/30">LIVE</span>
                </div>

                <div className="flex items-end gap-3">
                    <span className="text-3xl font-mono font-bold text-white">0.95</span>
                    <span className="text-sm font-bold text-yellow-500 mb-1">NEUTRAL</span>
                </div>

                <div className="mt-3 h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-yellow-500 w-[50%]" />
                </div>
                <div className="flex justify-between text-[10px] text-gray-500 mt-1 font-mono">
                    <span>Bearish &#60; 0.8</span>
                    <span>Bullish &#62; 1.2</span>
                </div>
            </div>

            {/* GUARDIAN STATUS (Phase 2 Placeholder) */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <Shield className="text-spidy-primary" size={16} />
                        Profit Guardian
                    </h3>
                    <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                        <span className="text-[10px] text-gray-500 uppercase block mb-1">Max Loss</span>
                        <span className="text-lg font-mono font-bold text-red-400">-₹2000</span>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                        <span className="text-[10px] text-gray-500 uppercase block mb-1">Daily Target</span>
                        <span className="text-lg font-mono font-bold text-green-400">+₹5000</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
