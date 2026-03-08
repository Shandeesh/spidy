import React, { useState } from 'react';
import { Activity, Shield, Wallet, TrendingUp, TrendingDown, DollarSign, Clock, Hash, Lock, ShieldCheck, FileKey, Zap, Check, ChevronDown, Download } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Combobox } from '@headlessui/react';
import axios from 'axios';
import CloudManager from './CloudManager';

// Anime Physics Variants
const animeAppear = {
    hidden: { opacity: 0, scale: 0.8, filter: 'blur(10px)' },
    visible: {
        opacity: 1,
        scale: 1,
        filter: 'blur(0px)',
        transition: { type: "spring", stiffness: 300, damping: 20 }
    },
    exit: { opacity: 0, scale: 0.8, filter: 'blur(10px)' }
};

export default function ShoongaDashboard({ mt5Status, logs, logsEndRef }) {

    // Manual Trading State
    const [manualSymbol, setManualSymbol] = useState("USDINR");
    const [manualVolume, setManualVolume] = useState("1"); // 1 Lot for NSE
    const [loading, setLoading] = useState(false);
    const [availableSymbols, setAvailableSymbols] = useState(["USDINR", "EURINR", "GBPINR", "JPYINR", "NIFTY", "BANKNIFTY"]);
    const [query, setQuery] = useState('');
    const [selectedTrade, setSelectedTrade] = useState(null);

    // HISTORY STATE
    const [showHistory, setShowHistory] = useState(false);
    const [tradeHistory, setTradeHistory] = useState([]);

    // SORT STATE
    const [sortConfig, setSortConfig] = useState({ key: 'time', direction: 'desc' });

    const handleSort = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }));
    };

    const getSortedPositions = () => {
        if (!mt5Status.positions) return [];
        const sorted = [...mt5Status.positions];
        sorted.sort((a, b) => {
            let valA = a[sortConfig.key];
            let valB = b[sortConfig.key];

            // Special handling for numbers
            if (sortConfig.key === 'profit' || sortConfig.key === 'volume' || sortConfig.key === 'price') {
                valA = parseFloat(valA);
                valB = parseFloat(valB);
            }

            if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
            if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
        return sorted;
    };

    // Auto-Secure State (Placeholder for now until Phase 2)
    const [autoSecureEnabled, setAutoSecureEnabled] = useState(false);
    const [secureThreshold, setSecureThreshold] = useState("500.0"); // INR

    const filteredSymbols =
        query === ''
            ? availableSymbols
            : availableSymbols.filter((s) => {
                return s.toLowerCase().includes(query.toLowerCase())
            })

    // Helpers
    const isProfitable = parseFloat(mt5Status.profit) >= 0;

    const handleManualTrade = async (action) => {
        setLoading(true);
        console.log(`[Shoonga] ${action} ${manualSymbol} ${manualVolume}`);

        try {
            const res = await axios.post('http://localhost:8001/trade', {
                action: action,
                symbol: manualSymbol,
                volume: manualVolume
            });
            console.log("Trade Response:", res.data);
            if (res.data.status.includes("REJECTED")) {
                alert(`Trade Rejected: ${res.data.reason}`);
            } else {
                alert(`Trade Accepted: ${res.data.status}`);
            }
        } catch (e) {
            console.error("Trade Error", e);
            alert("Failed to send trade command.");
        }
        setLoading(false);
    };

    // Pulse Colors
    const getPulseColor = (status) => {
        if (status === "BULLISH") return "text-green-400";
        if (status === "BEARISH") return "text-red-400";
        return "text-gray-400";
    };

    return (
        <div className="flex flex-col gap-6 h-full pr-2 overflow-hidden">

            {/* Account Stats Bar (Fixed Top) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-shrink-0">
                <StatCard
                    label="Shoonya Balance"
                    value={`₹${mt5Status.shoonya_balance || '0.00'}`}
                    icon={<Wallet size={24} className="text-orange-400" />}
                    active={true}
                    delay={0}
                />
                <StatCard
                    label="Shoonga Equity"
                    value={`₹${mt5Status.shoonya_equity || '0.00'}`}
                    icon={<DollarSign size={24} className="text-purple-400" />}
                    highlight
                    active={true}
                    delay={0.1}
                />
                <StatCard
                    label="Open P&L"
                    value={`₹${mt5Status.shoonya_profit || '0.00'}`}
                    icon={parseFloat(mt5Status.shoonya_profit || 0) >= 0 ? <TrendingUp size={24} className="text-green-400" /> : <TrendingDown size={24} className="text-red-400" />}
                    valueColor={parseFloat(mt5Status.shoonya_profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                    borderColor={parseFloat(mt5Status.shoonya_profit || 0) >= 0 ? 'border-green-500/30' : 'border-red-500/30'}
                    glow={parseFloat(mt5Status.shoonya_profit || 0) >= 0 ? 'shadow-green-500/10' : 'shadow-red-500/10'}
                    active={true}
                    delay={0.2}
                />
            </div>

            {/* Main Content Area (Flex Grow) */}
            <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">

                {/* Left Column: Active Trades & History Table */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                    className="lg:col-span-2 lg:w-2/3 bg-gradient-to-b from-white/10 to-white/5 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden flex flex-col shadow-xl"
                >
                    {/* STATUS BANNER */}
                    <div className="border-b border-white/10">
                        <div className="w-full bg-orange-500/10 py-3 flex flex-col items-center justify-center gap-1 border-b border-orange-500/20">
                            <div className="flex items-center gap-3">
                                <Activity size={20} className="text-orange-500 animate-pulse" />
                                <h2 className="text-lg font-bold text-orange-500 tracking-widest uppercase font-mono">
                                    SHOONYA BRIDGE ACTIVE
                                </h2>
                            </div>
                            <p className="text-[10px] font-mono text-orange-400 font-bold uppercase tracking-widest">
                                NSE MARKET OPEN • CONNECTED
                            </p>
                        </div>
                    </div>
                    {/* GLOBAL PULSE BAR */}
                    <div className="grid grid-cols-3 border-b border-white/10 bg-black/20">
                        <div className="p-2 border-r border-white/5 flex flex-col items-center justify-center">
                            <span className="text-[10px] text-gray-500 font-bold uppercase">Sentiment</span>
                            <span className={`text-xs font-mono font-bold ${getPulseColor(mt5Status.global_pulse?.sentiment)}`}>
                                {mt5Status.global_pulse?.sentiment || "NEUTRAL"}
                            </span>
                        </div>
                        <div className="p-2 border-r border-white/5 flex flex-col items-center justify-center">
                            <span className="text-[10px] text-gray-500 font-bold uppercase">Oil (Brent)</span>
                            <span className={`text-xs font-mono font-bold ${getPulseColor(mt5Status.global_pulse?.oil_status)}`}>
                                {mt5Status.global_pulse?.oil_status || "NEUTRAL"}
                            </span>
                        </div>
                        <div className="p-2 flex flex-col items-center justify-center">
                            <span className="text-[10px] text-gray-500 font-bold uppercase">DXY (Shield)</span>
                            <span className={`text-xs font-mono font-bold ${getPulseColor(mt5Status.global_pulse?.dxy_status)}`}>
                                {mt5Status.global_pulse?.dxy_status || "NEUTRAL"}
                            </span>
                        </div>
                    </div>

                    {/* TABS HEADER */}
                    <div className="flex border-b border-white/10">
                        <button
                            onClick={() => setShowHistory(false)}
                            className={`flex-1 p-4 flex justify-center items-center gap-2 font-bold tracking-wide transition-colors ${!showHistory ? 'bg-white/10 text-spidy-primary border-b-2 border-spidy-primary' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Activity size={18} />
                            SHOONGA POSITIONS
                        </button>
                        <button
                            onClick={() => setShowHistory(true)}
                            className={`flex-1 p-4 flex justify-center items-center gap-2 font-bold tracking-wide transition-colors ${showHistory ? 'bg-white/10 text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Clock size={18} />
                            TRADE HISTORY
                        </button>
                    </div>

                    {/* TABLE CONTENT (Placeholder until real data) */}
                    <div className="flex-1 overflow-x-auto p-2 overflow-y-auto">
                        <div className="p-12 text-center text-gray-600">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                                    <Activity className="text-gray-600" size={32} />
                                </div>
                                <p className="text-lg font-medium text-gray-500">No Active Shoonga Positions</p>
                                <p className="text-sm">Trades executed by Shoonya API will appear here.</p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Right Column: Controls, Security & Logs (Fixed Layout) */}
                <div className="flex flex-col gap-4 lg:w-1/3 h-full">

                    {/* CLOUD MANAGER */}
                    <CloudManager />

                    {/* COMMAND CONSOLE (Fixed) */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.35 }}
                        className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-5 flex flex-col gap-4 shadow-xl flex-shrink-0"
                    >
                        <div className="flex items-center justify-between border-b border-white/10 pb-2">
                            <div className="flex items-center gap-2">
                                <Hash size={16} className="text-orange-500" />
                                <h3 className="text-sm font-bold text-gray-200 tracking-wide uppercase">Shoonga Control</h3>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] uppercase font-bold text-gray-500">Auto-Pilot</span>
                                <button className="w-8 h-4 rounded-full bg-gray-600 relative">
                                    <div className="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm translate-x-0" />
                                </button>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Symbol (NSE)</label>
                                    <div className="relative">
                                        <Combobox value={manualSymbol} onChange={setManualSymbol}>
                                            <div className="relative w-full cursor-default overflow-hidden rounded-lg bg-black/20 text-left border border-white/10 sm:text-sm">
                                                <Combobox.Input
                                                    className="w-full border-none py-2 pl-3 pr-10 text-xs font-mono leading-5 text-white bg-transparent focus:ring-0 focus:outline-none uppercase"
                                                    onChange={(event) => setQuery(event.target.value)}
                                                    displayValue={(person) => person}
                                                />
                                            </div>
                                            {/* Options omitted for brevity in placeholder */}
                                        </Combobox>
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Lots</label>
                                    <input
                                        type="number"
                                        value={manualVolume}
                                        onChange={(e) => setManualVolume(e.target.value)}
                                        className="bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white text-center"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3 mt-1">
                                <button onClick={() => handleManualTrade('BUY')} className="bg-green-500/10 border border-green-500/30 text-green-400 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-2">
                                    <TrendingUp size={14} /> BUY
                                </button>
                                <button onClick={() => handleManualTrade('SELL')} className="bg-red-500/10 border border-red-500/30 text-red-400 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-2">
                                    <TrendingDown size={14} /> SELL
                                </button>
                            </div>
                        </div>
                    </motion.div>

                    {/* SHOONGA LOGS */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4 }}
                        className="bg-black/80 backdrop-blur-xl rounded-2xl border border-gray-800 p-0 flex flex-col flex-1 overflow-hidden min-h-0 shadow-2xl"
                    >
                        <div className="p-3 bg-gray-900/50 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
                            <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-bold text-gray-400 tracking-wider">SHOONGA_LOGS.sh</span>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1.5 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
                            {logs && logs.length > 0 ? (
                                logs.map((log, i) => (
                                    <div key={i} className="text-gray-400 break-all border-b border-white/5 pb-1 mb-1 last:border-0 last:pb-0 last:mb-0">
                                        <span className="text-green-500 mr-2">$</span>
                                        {log}
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-600 italic opacity-50">Waiting for Shoonga backend events...</p>
                            )}
                            <div ref={logsEndRef} />
                        </div>
                    </motion.div>

                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value, icon, highlight, valueColor, borderColor, glow, active, delay }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, type: "spring", stiffness: 300, damping: 20 }}
            className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br p-6 transition-all duration-300
                ${highlight ? 'from-spidy-primary/20 to-spidy-primary/5 border-spidy-primary/50' : 'from-white/10 to-white/5 border-white/10'}
                ${borderColor ? `border-${borderColor}` : ''}
                ${glow ? `shadow-lg ${glow}` : 'shadow-xl'}
            `}
        >
            <div className="flex items-center justify-between relative z-10">
                <div>
                    <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">{label}</h3>
                    <div className={`text-2xl font-bold font-mono tracking-tight ${valueColor || 'text-white'}`}>
                        {active ? value : <div className="h-8 w-24 bg-white/10 rounded animate-pulse" />}
                    </div>
                </div>
                <div className={`p-3 rounded-xl ${highlight ? 'bg-spidy-primary/20' : 'bg-black/20'} backdrop-blur-md`}>
                    {icon}
                </div>
            </div>
        </motion.div>
    );
}

function SecurityItem({ label, status, icon, color, details }) {
    const [isOpen, setIsOpen] = useState(false);
    React.useEffect(() => {
        let timer;
        if (isOpen) { timer = setTimeout(() => { setIsOpen(false); }, 4000); }
        return () => clearTimeout(timer);
    }, [isOpen]);

    return (
        <motion.div
            layout onClick={() => setIsOpen(!isOpen)} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            className={`relative bg-white/5 border ${isOpen ? 'border-spidy-primary/50 bg-white/10 z-50' : 'border-white/5 z-0'} rounded-lg p-3 flex items-center justify-between transition-all cursor-pointer select-none`}
        >
            <div className={`p-1.5 rounded-md bg-black/20 ${color}`}>{icon}</div>
            <div className="flex flex-col items-end">
                <span className="text-[10px] font-bold text-gray-500 uppercase">{label}</span>
                <span className={`text-xs font-mono font-bold ${color}`}>{status}</span>
            </div>
            {/* Details omitted for brevity in this clone */}
        </motion.div>
    );
}
