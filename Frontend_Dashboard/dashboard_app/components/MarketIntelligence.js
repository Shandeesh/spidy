import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

// Fear & Greed Gauge
const FearGreedGauge = ({ score }) => {
    const safeScore = Math.max(0, Math.min(100, score || 50));
    const angle = -90 + (safeScore / 100) * 180; // -90deg (fear) to +90deg (greed)

    const getColor = (s) => {
        if (s <= 25) return '#ef4444';      // Extreme Fear - red
        if (s <= 40) return '#f97316';      // Fear - orange
        if (s <= 60) return '#eab308';      // Neutral - yellow
        if (s <= 75) return '#84cc16';      // Greed - lime
        return '#22c55e';                   // Extreme Greed - green
    };

    const color = getColor(safeScore);

    const getLabel = (s) => {
        if (s <= 25) return 'Extreme Fear';
        if (s <= 40) return 'Fear';
        if (s <= 60) return 'Neutral';
        if (s <= 75) return 'Greed';
        return 'Extreme Greed';
    };

    return (
        <div className="flex flex-col items-center gap-1">
            <div className="relative w-24 h-12 overflow-hidden">
                {/* Gauge Arc */}
                <svg viewBox="0 0 100 50" className="w-full">
                    {/* Background arc */}
                    <path d="M 5 50 A 45 45 0 0 1 95 50" fill="none" stroke="#1f2937" strokeWidth="8" strokeLinecap="round" />
                    {/* Gradient zones - Fear to Greed */}
                    <path d="M 5 50 A 45 45 0 0 1 30 12" fill="none" stroke="#ef4444" strokeWidth="8" strokeLinecap="round" opacity="0.5" />
                    <path d="M 30 12 A 45 45 0 0 1 50 5" fill="none" stroke="#f97316" strokeWidth="8" strokeLinecap="round" opacity="0.5" />
                    <path d="M 50 5 A 45 45 0 0 1 70 12" fill="none" stroke="#eab308" strokeWidth="8" strokeLinecap="round" opacity="0.5" />
                    <path d="M 70 12 A 45 45 0 0 1 95 50" fill="none" stroke="#22c55e" strokeWidth="8" strokeLinecap="round" opacity="0.5" />
                    {/* Needle */}
                    <g transform={`rotate(${angle}, 50, 50)`}>
                        <line x1="50" y1="50" x2="50" y2="10" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
                        <circle cx="50" cy="50" r="3" fill={color} />
                    </g>
                </svg>
            </div>
            <div className="text-center">
                <span className="text-xl font-black font-mono" style={{ color }}>{safeScore}</span>
                <p className="text-[9px] uppercase font-bold tracking-widest mt-0.5" style={{ color }}>{getLabel(safeScore)}</p>
            </div>
        </div>
    );
};

const SentimentBadge = ({ sentiment }) => {
    const s = sentiment || 'neutral';
    if (s.includes('positive')) return <span className="text-green-400 text-[10px] font-bold">🟢</span>;
    if (s.includes('negative')) return <span className="text-red-400 text-[10px] font-bold">🔴</span>;
    return <span className="text-gray-400 text-[10px] font-bold">⚪</span>;
};

export default function MarketIntelligence() {
    const [intel, setIntel] = useState(null);
    const [loading, setLoading] = useState(true);
    const REFRESH_INTERVAL = 30000; // 30 seconds

    const fetchIntel = async () => {
        try {
            const res = await axios.get('http://localhost:8000/market_intelligence', { timeout: 8000 });
            setIntel(res.data);
        } catch (e) {
            console.warn('Market Intelligence unavailable:', e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchIntel();
        const interval = setInterval(fetchIntel, REFRESH_INTERVAL);
        return () => clearInterval(interval);
    }, []);

    const fg = intel?.fear_greed || { score: 50, label: 'Neutral' };
    const nextEvent = intel?.next_high_impact_event;
    const headlines = intel?.top_headlines || [];
    const macroBias = intel?.macro_bias || 'NEUTRAL';
    const macroNote = intel?.macro_note || '';

    const biasColor = {
        STRONG_BUY: 'text-green-400', BUY: 'text-green-500',
        NEUTRAL: 'text-yellow-400',
        SELL: 'text-red-400', STRONG_SELL: 'text-red-500',
    }[macroBias] || 'text-yellow-400';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-black/30 backdrop-blur-md rounded-xl border border-white/10 p-4 flex flex-col gap-3"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                    <span className="text-yellow-400">◆</span> Market Intelligence
                </h3>
                {loading && <div className="w-3 h-3 border-2 border-yellow-400/50 border-t-yellow-400 rounded-full animate-spin" />}
            </div>

            {/* Fear & Greed + Macro Bias Row */}
            <div className="flex items-center gap-4">
                <FearGreedGauge score={fg.score} />
                <div className="flex flex-col gap-1 flex-1">
                    <div className="text-[9px] text-gray-500 uppercase tracking-widest">Macro Bias</div>
                    <span className={`text-sm font-black uppercase tracking-wider ${biasColor}`}>{macroBias.replace('_', ' ')}</span>
                    <p className="text-[9px] text-gray-500 leading-tight">{macroNote}</p>
                </div>
            </div>

            {/* Next High-Impact Event */}
            {nextEvent && nextEvent.event && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 flex items-start gap-2">
                    <span className="text-red-400 text-sm mt-0.5">⚠️</span>
                    <div className="flex flex-col gap-0.5">
                        <p className="text-[10px] font-bold text-red-300 uppercase tracking-wide">HIGH-IMPACT EVENT</p>
                        <p className="text-[10px] text-red-200">{nextEvent.event}</p>
                        <p className="text-[9px] text-red-400/70">{nextEvent.minutes_away}min away • {nextEvent.time_utc}</p>
                    </div>
                </div>
            )}

            {/* Top Headlines */}
            {headlines.length > 0 && (
                <div className="flex flex-col gap-1.5">
                    <p className="text-[9px] uppercase tracking-widest text-gray-600 font-bold">Top News</p>
                    {headlines.slice(0, 4).map((h, i) => (
                        <div key={i} className="flex items-start gap-2 group">
                            <SentimentBadge sentiment={h.sentiment} />
                            <div className="flex-1 min-w-0">
                                <p className="text-[10px] text-gray-300 leading-tight line-clamp-2 group-hover:text-white transition-colors">
                                    {h.title}
                                </p>
                                <p className="text-[8px] text-gray-600 mt-0.5">{h.source} • {h.impact}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!intel && !loading && (
                <p className="text-[10px] text-gray-600 text-center">Connect bridge to enable Market Intelligence</p>
            )}
        </motion.div>
    );
}
