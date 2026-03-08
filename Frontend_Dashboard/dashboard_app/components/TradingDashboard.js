import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Shield, Wallet, TrendingUp, TrendingDown, DollarSign, Clock, Hash, Lock, ShieldCheck, FileKey, Zap, Check, ChevronDown, Download, X, RefreshCw } from 'lucide-react';
import { Combobox, Dialog } from '@headlessui/react';
import axios from 'axios';

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

const animeHover = {
    scale: 1.05,
    boxShadow: "0px 0px 8px rgb(var(--spidy-primary))",
    transition: { type: "spring", stiffness: 400, damping: 10 }
};

export default function TradingDashboard({ mt5Status, logs, logsEndRef }) {

    // Manual Trading State
    const [manualSymbol, setManualSymbol] = useState("EURUSD");
    const [manualVolume, setManualVolume] = useState("0.01");
    // Removed duplicate declaration
    const [loading, setLoading] = useState(false);
    const [availableSymbols, setAvailableSymbols] = useState([]);
    const [query, setQuery] = useState('');
    const [selectedTrade, setSelectedTrade] = useState(null); // For InfoModal

    // Helper: Format Reason for UI
    const getFormattedReason = (reason, strategy) => {
        // Priority 1: Specific Bot Close Actions
        const r = reason || "";
        if (r.includes("AutoSecure")) return "Secure (Auto)";
        if (r.includes("Secure Now")) return "Secure (Manual)";

        // Priority 2: Manual Close Override
        // If reason is explicitly "User" (Manual Close), show "User" regardless of strategy.
        if (r === "User" || r.includes("User") || r.includes("Client")) return "User";

        // Priority 3: Strategy Source (AI vs User)
        // If reason is SL/TP or Manual, we use the Strategy tag.
        const s = strategy || "Manual";
        if (s.includes("SmartPeak") || s.includes("HFT") || s.includes("Bot")) return "AI (SmartPeak)";

        // Default Fallback (Covers Manual, User, Stop Loss, Take Profit on manual trades)
        return "User";
    };

    // Modal Component
    const TradeDetailsModal = ({ trade, onClose }) => {
        if (!trade) return null;

        // Calcs
        const profitColor = trade.profit >= 0 ? "text-green-400" : "text-red-400";
        const entryPrice = parseFloat(trade.open_price);
        const exitPrice = parseFloat(trade.close_price);
        const profit = parseFloat(trade.profit);

        // Percent Return
        let pctChange = 0;
        if (entryPrice > 0) {
            pctChange = ((exitPrice - entryPrice) / entryPrice) * 100;
            if (trade.type === "SELL") pctChange *= -1;
        }

        // Duration
        let durationStr = "N/A";
        if (trade.open_time && trade.close_time) {
            const start = new Date(trade.open_time);
            const end = new Date(trade.close_time);
            const diffMs = end - start;
            if (!isNaN(diffMs)) {
                const mins = Math.floor(diffMs / 60000);
                const secs = Math.floor((diffMs % 60000) / 1000);
                const hours = Math.floor(mins / 60);
                durationStr = `${hours}h ${mins % 60}m ${secs}s`;
            }
        }

        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="bg-gray-900 border border-white/10 rounded-2xl shadow-2xl p-6 max-w-sm w-full relative overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                    onMouseLeave={onClose}
                >
                    {/* Background Glow */}
                    <div className={`absolute top-0 right-0 w-32 h-32 bg-${trade.profit >= 0 ? 'green' : 'red'}-500/10 blur-3xl rounded-full pointer-events-none`}></div>

                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                {trade.symbol}
                                <span className={`text-xs px-2 py-0.5 rounded ${trade.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                    {trade.type}
                                </span>
                            </h3>
                            <p className="text-xs text-gray-500 font-mono">#{trade.ticket}</p>
                        </div>
                        <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-full transition-colors">
                            <X size={18} className="text-gray-400" />
                        </button>
                    </div>

                    <div className="space-y-4">
                        {/* Main Result */}
                        <div className="flex items-center justify-between bg-white/5 p-4 rounded-xl border border-white/5">
                            <div className="flex flex-col">
                                <span className="text-xs text-gray-400 uppercase tracking-widest">Net Profit</span>
                                <span className={`text-2xl font-bold font-mono ${profitColor}`}>
                                    {profit >= 0 ? '+' : ''}{profit.toFixed(2)}
                                </span>
                            </div>
                            <div className="text-right flex flex-col items-end">
                                <span className={`text-sm font-mono font-bold ${pctChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                    {pctChange >= 0 ? '▲' : '▼'} {Math.abs(pctChange).toFixed(2)}%
                                </span>
                                <span className="text-[10px] text-gray-500">Price Change</span>
                            </div>
                        </div>

                        {/* Grid Details */}
                        <div className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
                            <div className="flex flex-col gap-1">
                                <span className="text-[10px] text-gray-500 uppercase">Close Reason</span>
                                <span className="font-bold text-gray-200">{getFormattedReason(trade.exit_reason, trade.strategy)}</span>
                                <span className="text-[9px] text-gray-600 truncate">{trade.exit_reason}</span>
                            </div>
                            <div className="flex flex-col gap-1 text-right">
                                <span className="text-[10px] text-gray-500 uppercase">Duration</span>
                                <span className="font-mono text-gray-300">{durationStr}</span>
                            </div>

                            <div className="flex flex-col gap-1 p-2 bg-black/20 rounded-lg">
                                <span className="text-[10px] text-gray-500 uppercase">Entry Price</span>
                                <span className="font-mono text-gray-300">{trade.open_price}</span>
                            </div>
                            <div className="flex flex-col gap-1 p-2 bg-black/20 rounded-lg text-right">
                                <span className="text-[10px] text-gray-500 uppercase">Exit Price</span>
                                <span className="font-mono text-gray-300">{trade.close_price}</span>
                            </div>
                            <div className="flex flex-col gap-1 col-span-2">
                                <span className="text-[10px] text-gray-500 uppercase">Time</span>
                                <div className="flex justify-between font-mono text-xs text-gray-400">
                                    <span>Open: {trade.open_time?.split(' ')[1]}</span>
                                    <span>Close: {trade.close_time?.split(' ')[1]}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        );
    };

    // Jitter removed - using real latency only
    const [sessionId] = useState(Math.random().toString(36).substring(7).toUpperCase()); // Client Session ID

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

    // AUTO-SECURE STATE
    const [autoSecureEnabled, setAutoSecureEnabled] = useState(() => {
        // Initialize from LocalStorage if available (Instant UX)
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('spidy_auto_secure_enabled');
            return saved === 'true';
        }
        return false;
    });
    const [secureThreshold, setSecureThreshold] = useState(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('spidy_auto_secure_threshold');
            return saved || "10.0";
        }
        return "10.0";
    });
    const [savingSecure, setSavingSecure] = useState(false);


    const filteredSymbols =
        query === ''
            ? availableSymbols
            : availableSymbols.filter((s) => {
                return s.toLowerCase().includes(query.toLowerCase())
            })

    // Fetch Symbols & History
    React.useEffect(() => {
        const fetchSymbols = async (retries = 5) => {
            try {
                const res = await axios.get('http://localhost:8000/symbols');
                if (res.data && res.data.symbols) {
                    setAvailableSymbols(res.data.symbols);
                }
            } catch (e) {
                console.warn(`Fetch Symbols Failed. Retries left: ${retries}`, e.message);
                if (retries > 0) {
                    setTimeout(() => fetchSymbols(retries - 1), 3000); // Retry every 3s
                }
            }
        };

        const fetchSettings = async () => {
            try {
                const res = await axios.get('http://localhost:8000/status');
                if (res.data && res.data.risk_settings && res.data.risk_settings.auto_secure) {
                    const conf = res.data.risk_settings.auto_secure;
                    setAutoSecureEnabled(conf.enabled);
                    setSecureThreshold(conf.threshold);
                }
            } catch (e) {
                console.warn("Fetch Settings Failed", e);
            }
        };

        const fetchHistory = async () => {
            try {
                const res = await axios.get('http://localhost:8000/history');
                if (res.data && res.data.history) {
                    setTradeHistory(res.data.history);
                }
            } catch (e) {
                console.error("Failed to fetch history", e);
            }
        };

        fetchSymbols();
        fetchSettings();
        fetchHistory();

        // Poll History and Settings occasionally to keep it fresh without spamming
        const histInterval = setInterval(() => {
            fetchHistory();
            fetchSettings();
        }, 10000);
        return () => clearInterval(histInterval);
    }, []);



    // Helpers
    const isProfitable = parseFloat(mt5Status.profit) >= 0;

    const handleManualTrade = async (action) => {
        setLoading(true);
        try {
            await axios.post('http://localhost:8000/trade', {
                action: action,
                symbol: manualSymbol,
                volume: manualVolume
            });
        } catch (e) {
            console.error("Trade Failed", e);
        }
        setLoading(false);
    };

    const toggleAutoTrading = async () => {
        try {
            await axios.post('http://localhost:8000/toggle_auto', {
                enable: !mt5Status.auto_trading
            });
        } catch (e) {
            console.error("Toggle Failed", e);
        }
    };

    const handleCloseTrade = async (pos) => {
        if (!confirm(`Close position ${pos.ticket} (${pos.symbol})?`)) return;

        try {
            await axios.post('http://localhost:8000/close_trade', {
                ticket: pos.ticket,
                symbol: pos.symbol
            });
        } catch (e) {
            console.error("Close Trade Failed", e);
            alert("Failed to close trade: " + e.message);
        }
    };

    // Auto-Secure Handler
    const handleUpdateSecure = async (newEnabled, newThreshold) => {
        setSavingSecure(true);
        try {
            const payload = {};
            if (newEnabled !== undefined) payload.enabled = newEnabled;
            if (newThreshold !== undefined) payload.threshold = parseFloat(newThreshold);

            const res = await axios.post('http://localhost:8000/settings/auto_secure', payload);
            if (res.data.status === "UPDATED") {
                if (newEnabled !== undefined) {
                    setAutoSecureEnabled(newEnabled);
                    localStorage.setItem('spidy_auto_secure_enabled', newEnabled);
                }
                if (newThreshold !== undefined) {
                    setSecureThreshold(newThreshold);
                    localStorage.setItem('spidy_auto_secure_threshold', newThreshold);
                }
            }
        } catch (e) {
            console.error("Update Secure Failed", e);
        }
        setSavingSecure(false);
    };

    const handleSecureNow = async () => {
        if (!confirm("Secure ALL profitable trades immediately?")) return;
        try {
            // "Secure Now" means "Close all Green trades", ignoring the Auto-Secure Target.
            // We pass threshold: 0 to ensure anything with Net Profit > 0 is closed.
            await axios.post('http://localhost:8000/close_all_trades', {
                profitable_only: true,
                threshold: 0.0
            });
            // Refresh history/positions roughly
            setTimeout(() => {
                // Trigger re-fetch if we had those functions exposed or fail-safe via standard polling
            }, 1000);
        } catch (e) {
            alert("Failed to secure profits: " + e.message);
        }
    };

    return (
        <div className="flex flex-col gap-6 h-full pr-2 overflow-hidden relative">
            <TradeDetailsModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />

            {/* Account Stats Bar (Fixed Top) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-shrink-0">
                <StatCard
                    label="Balance"
                    value={`$${typeof mt5Status.balance === 'number' ? mt5Status.balance.toFixed(2) : (mt5Status.balance || '0.00')}`}
                    icon={<Wallet size={24} className="text-blue-400" />}
                    active={mt5Status.connected}
                    delay={0}
                />
                <StatCard
                    label="Equity"
                    value={`$${typeof mt5Status.equity === 'number' ? mt5Status.equity.toFixed(2) : (mt5Status.equity || '0.00')}`}
                    icon={<DollarSign size={24} className="text-purple-400" />}
                    highlight
                    active={mt5Status.connected}
                    delay={0.1}
                />
                <StatCard
                    label="Open Profit"
                    value={`$${typeof mt5Status.profit === 'number' ? mt5Status.profit.toFixed(2) : (mt5Status.profit || '0.00')}`}
                    icon={isProfitable ? <TrendingUp size={24} className="text-green-400" /> : <TrendingDown size={24} className="text-red-400" />}
                    valueColor={isProfitable ? 'text-green-400' : 'text-red-400'}
                    borderColor={isProfitable ? 'border-green-500/30' : 'border-red-500/30'}
                    glow={isProfitable ? 'shadow-green-500/10' : 'shadow-red-500/10'}
                    active={mt5Status.connected}
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
                    {/* STATUS BANNER (Large & Detailed) */}
                    <div className="border-b border-white/10">
                        {!mt5Status.connected ? (
                            <div className="w-full bg-red-500/20 py-3 flex items-center justify-center gap-3 animate-pulse">
                                <ShieldCheck size={20} className="text-red-500" />
                                <h2 className="text-lg font-bold text-red-500 tracking-widest uppercase">
                                    CONNECTION LOST - RETRYING...
                                </h2>
                            </div>
                        ) : mt5Status.market_status === 'ALGO_DISABLED' ? (
                            <div className="w-full bg-red-500/20 py-4 flex flex-col items-center justify-center gap-1 border-b border-red-500/40 animate-pulse">
                                <div className="flex items-center gap-3">
                                    <Lock size={24} className="text-red-500" />
                                    <h2 className="text-xl font-black text-red-500 tracking-widest uppercase font-mono">
                                        PERMISSION DENIED
                                    </h2>
                                </div>
                                <p className="text-xs font-mono text-red-400 font-bold uppercase tracking-widest text-center px-4">
                                    Algo Trading Disabled in MT5 Terminal. Please Enable it to Trade.
                                </p>
                            </div>
                        ) : mt5Status.market_status === 'CLOSED_WEEKEND' ? (
                            <div className="w-full bg-yellow-500/10 py-4 flex flex-col items-center justify-center gap-1 border-b border-yellow-500/20">
                                <div className="flex items-center gap-3">
                                    <Clock size={24} className="text-yellow-500" />
                                    <h2 className="text-xl font-black text-yellow-500 tracking-widest uppercase font-mono">
                                        MARKET CLOSED - WEEKEND
                                    </h2>
                                </div>
                                <p className="text-xs font-mono text-yellow-600 font-bold uppercase tracking-widest">
                                    SERVER TIME: {mt5Status.server_time || "--:--:--"} • MODE: {mt5Status.auto_trading ? "AUTO" : "MANUAL"}
                                </p>
                            </div>
                        ) : mt5Status.auto_trading ? (
                            <div className="w-full bg-green-500/10 py-3 flex flex-col items-center justify-center gap-1 border-b border-green-500/20">
                                <div className="flex items-center gap-3">
                                    <Activity size={20} className="text-green-500 animate-pulse" />
                                    <h2 className="text-lg font-bold text-green-500 tracking-widest uppercase font-mono">
                                        AUTO-TRADER ACTIVE
                                    </h2>
                                </div>
                                <p className="text-[10px] font-mono text-green-600 font-bold uppercase tracking-widest">
                                    {mt5Status.market_status || "MARKET OPEN"} • {mt5Status.server_time || "--:--:--"}
                                </p>
                            </div>
                        ) : (
                            <div className="w-full bg-blue-500/10 py-3 flex flex-col items-center justify-center gap-1 border-b border-blue-500/20">
                                <div className="flex items-center gap-3">
                                    <Hash size={20} className="text-blue-500" />
                                    <h2 className="text-lg font-bold text-blue-500 tracking-widest uppercase font-mono">
                                        MANUAL TRADING MODE
                                    </h2>
                                </div>
                                <p className="text-[10px] font-mono text-blue-400 font-bold uppercase tracking-widest">
                                    {mt5Status.market_status || "MARKET OPEN"} • {mt5Status.server_time || "--:--:--"}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* MACRO ORGANS STATUS BAR */}
                    {mt5Status.connected && (
                        <div className="w-full bg-black/40 border-b border-white/5 py-2 px-4 flex items-center justify-between text-[10px] font-mono font-bold tracking-widest uppercase text-gray-400">
                            <div className="flex items-center gap-4">
                                {/* 1. Global Sentiment */}
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500">SENTIMENT:</span>
                                    <span className={`${mt5Status.sentiment === 'BULLISH' ? 'text-green-400' : mt5Status.sentiment === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                                        {mt5Status.sentiment || "NEUTRAL"}
                                    </span>
                                </div>

                                {/* 2. The Oil Watcher */}
                                {mt5Status.oil && mt5Status.oil.symbol && (
                                    <div className="flex items-center gap-2 border-l border-white/10 pl-4">
                                        <span className="text-gray-500">OIL:</span>
                                        <span className={`${mt5Status.oil.change_pct >= 0 ? 'text-green-400' : 'text-red-400'} flex items-center gap-1`}>
                                            {mt5Status.oil.symbol} {mt5Status.oil.change_pct > 0 ? '+' : ''}{parseFloat(mt5Status.oil.change_pct).toFixed(2)}%
                                            {Math.abs(mt5Status.oil.change_pct) >= 2.0 && <Zap size={10} className="text-yellow-400 animate-pulse" />}
                                        </span>
                                    </div>
                                )}

                                {/* 3. Global Shield (DXY) */}
                                {mt5Status.dxy && mt5Status.dxy.status && (
                                    <div className="flex items-center gap-2 border-l border-white/10 pl-4">
                                        <span className="text-gray-500">SHIELD (DXY):</span>
                                        <span className={`${mt5Status.dxy.status === 'BULLISH' ? 'text-green-400' : mt5Status.dxy.status === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}`}>
                                            {mt5Status.dxy.status} ({mt5Status.dxy.change_pct > 0 ? '+' : ''}{parseFloat(mt5Status.dxy.change_pct || 0).toFixed(2)}%)
                                        </span>
                                    </div>
                                )}
                            </div>

                            {/* Right Side: Risk Mode */}
                            <div className="flex items-center gap-2">
                                <span className="text-gray-500">RISK:</span>
                                <span className="text-spidy-primary">{mt5Status.risk_settings?.mode || "STANDARD"}</span>
                            </div>
                        </div>
                    )}

                    {/* TABS HEADER */}
                    <div className="flex border-b border-white/10">
                        <button
                            onClick={() => setShowHistory(false)}
                            className={`flex-1 p-4 flex justify-center items-center gap-2 font-bold tracking-wide transition-colors ${!showHistory ? 'bg-white/10 text-spidy-primary border-b-2 border-spidy-primary' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Activity size={18} />
                            {/* UPGRADE 12: Show open position count badge */}
                            ACTIVE POSITIONS
                            {mt5Status.positions && mt5Status.positions.length > 0 && (
                                <span className="ml-1 bg-spidy-primary text-white text-[10px] font-black px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                                    {mt5Status.positions.length}
                                </span>
                            )}
                        </button>
                        <button
                            onClick={() => setShowHistory(true)}
                            className={`flex-1 p-4 flex justify-center items-center gap-2 font-bold tracking-wide transition-colors ${showHistory ? 'bg-white/10 text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Clock size={18} />
                            TRADE HISTORY
                        </button>
                    </div>

                    <div className="flex-1 overflow-x-auto p-2 overflow-y-auto">
                        {!showHistory ? (
                            // ACTIVE TRADES TABLE
                            <table className="w-full text-left text-sm text-gray-400 border-separate border-spacing-y-1">
                                <thead>
                                    <tr className="text-xs uppercase font-bold text-gray-500 tracking-wider">
                                        <th className="px-4 py-2 cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('symbol')}>
                                            <div className="flex items-center gap-1">
                                                Symbol
                                                {sortConfig.key === 'symbol' && (sortConfig.direction === 'asc' ? <ChevronDown size={12} /> : <div className="transform rotate-180"><ChevronDown size={12} /></div>)}
                                            </div>
                                        </th>
                                        <th className="px-4 py-2">Side</th>
                                        <th className="px-4 py-2 cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('volume')}>
                                            <div className="flex items-center gap-1">
                                                Size
                                                {sortConfig.key === 'volume' && (sortConfig.direction === 'asc' ? <ChevronDown size={12} /> : <div className="transform rotate-180"><ChevronDown size={12} /></div>)}
                                            </div>
                                        </th>
                                        <th className="px-4 py-2">Date</th>
                                        <th className="px-4 py-2 cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('time')}>
                                            <div className="flex items-center gap-1">
                                                Time
                                                {sortConfig.key === 'time' && (sortConfig.direction === 'asc' ? <ChevronDown size={12} /> : <div className="transform rotate-180"><ChevronDown size={12} /></div>)}
                                            </div>
                                        </th>
                                        <th className="px-4 py-2">Entry</th>
                                        {/* UPGRADE 10: ROI% column header */}
                                        <th className="px-4 py-2 text-center text-yellow-500/70">ROI%</th>
                                        <th className="px-4 py-2 text-right cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('profit')}>
                                            <div className="flex items-center justify-end gap-1">
                                                P/L
                                                {sortConfig.key === 'profit' && (sortConfig.direction === 'asc' ? <ChevronDown size={12} /> : <div className="transform rotate-180"><ChevronDown size={12} /></div>)}
                                            </div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <AnimatePresence>
                                        {mt5Status.positions && mt5Status.positions.length > 0 ? (
                                            getSortedPositions().map((pos, i) => (
                                                <motion.tr
                                                    key={pos.ticket}
                                                    variants={animeAppear}
                                                    initial="hidden"
                                                    animate="visible"
                                                    exit="exit"
                                                    layout
                                                    className="bg-white/5 hover:bg-white/10 transition-colors group relative overflow-hidden"
                                                >
                                                    <td className="px-4 py-3 font-bold text-white rounded-l-xl border-l-4 border-transparent group-hover:border-spidy-primary transition-all">
                                                        {pos.symbol}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${pos.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                            {pos.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-300">{pos.volume}</td>
                                                    <td className="px-4 py-3 font-mono text-gray-400 text-xs">
                                                        {pos.time ? pos.time.split(' ')[0] : '--'}
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-400 text-xs">
                                                        {pos.time ? pos.time.split(' ')[1] : '--:--'}
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-300">{pos.price}</td>
                                                    {/* UPGRADE 10: ROI% = profit / balance * 100 */}
                                                    <td className="px-4 py-3 text-center">
                                                        {(() => {
                                                            const balance = parseFloat(mt5Status.balance) || 1;
                                                            const roi = (pos.profit / balance) * 100;
                                                            return (
                                                                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${roi >= 0 ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'
                                                                    }`}>
                                                                    {roi >= 0 ? '+' : ''}{roi.toFixed(2)}%
                                                                </span>
                                                            );
                                                        })()}
                                                    </td>
                                                    <td className={`px-4 py-3 font-mono font-bold text-right rounded-r-xl ${pos.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {/* UPGRADE 11: P&L with mini progress bar */}
                                                        <div className="flex flex-col items-end gap-0.5">
                                                            <span>{pos.profit >= 0 ? '+' : ''}{pos.profit.toFixed(2)}</span>
                                                            <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden min-w-[40px]">
                                                                <div
                                                                    className={`h-full rounded-full transition-all duration-500 ${pos.profit >= 0 ? 'bg-green-400' : 'bg-red-400'
                                                                        }`}
                                                                    style={{ width: `${Math.min(Math.abs(pos.profit / (parseFloat(mt5Status.balance) || 1)) * 2000, 100)}%` }}
                                                                />
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleCloseTrade(pos); }}
                                                            className="ml-3 text-[10px] bg-red-500/20 hover:bg-red-500/40 text-red-300 border border-red-500/30 px-2 py-1 rounded transition-colors uppercase font-bold"
                                                        >
                                                            Close
                                                        </button>
                                                    </td>
                                                </motion.tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="7" className="p-12 text-center text-gray-600">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                                                            <Activity className="text-gray-600" size={32} />
                                                        </div>
                                                        <p className="text-lg font-medium text-gray-500">No Active Positions</p>
                                                        <p className="text-sm">Trades executed by Spidy will appear here.</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        ) : (
                            // HISTORY TABLE
                            <table className="w-full text-left text-sm text-gray-400 border-separate border-spacing-y-1">
                                <thead>
                                    <tr className="text-xs uppercase font-bold text-gray-500 tracking-wider">
                                        <th className="px-4 py-2">Symbol</th>
                                        <th className="px-4 py-2">Side</th>
                                        <th className="px-4 py-2">Size</th>
                                        <th className="px-4 py-2">Closed Date</th>
                                        <th className="px-4 py-2 text-right">Time</th>
                                        <th className="px-4 py-2">Price</th>
                                        <th className="px-4 py-2 text-right">Profit</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <AnimatePresence>
                                        {tradeHistory && tradeHistory.length > 0 ? (
                                            tradeHistory.map((deal, i) => (
                                                <motion.tr
                                                    key={deal.ticket || i}
                                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                                    className="bg-white/5 hover:bg-white/10 transition-colors group"
                                                >
                                                    <td className="px-4 py-3 font-bold text-gray-300 rounded-l-xl">
                                                        {deal.symbol}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${deal.type === 'BUY' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                                                            {deal.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-500">{deal.volume}</td>
                                                    <td className="px-4 py-3 font-mono text-gray-400 text-xs">
                                                        {deal.close_time ? deal.close_time.split(' ')[0] : '--'}
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-400 text-xs text-right">
                                                        {deal.close_time ? deal.close_time.split(' ')[1] : (deal.open_time ? deal.open_time.split(' ')[1] : '--:--')}
                                                    </td>
                                                    <td className="px-4 py-3 font-mono text-gray-400">{deal.close_price}</td>
                                                    <td className={`px-4 py-3 font-mono font-bold text-right rounded-r-xl ${deal.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {deal.profit >= 0 ? '+' : ''}{deal.profit.toFixed(2)}
                                                    </td>
                                                </motion.tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="7" className="p-12 text-center text-gray-600">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                                                            <Clock className="text-gray-600" size={32} />
                                                        </div>
                                                        <p className="text-lg font-medium text-gray-500">No History Available</p>
                                                        <p className="text-sm">Closed trades will be listed here.</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        )}
                    </div>
                </motion.div>

                {/* Right Column: Controls, Security & Logs (Fixed Layout) */}
                <div className="flex flex-col gap-4 lg:w-1/3 h-full">

                    {/* COMMAND CONSOLE (Fixed) */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.35 }}
                        className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-5 flex flex-col gap-4 shadow-xl flex-shrink-0"
                    >
                        <div className="flex items-center justify-between border-b border-white/10 pb-2">
                            <div className="flex items-center gap-2">
                                <Hash size={16} className="text-spidy-primary" />
                                <h3 className="text-sm font-bold text-gray-200 tracking-wide uppercase">Command Console</h3>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] uppercase font-bold text-gray-500">Auto-Pilot</span>
                                <button
                                    onClick={toggleAutoTrading}
                                    className={`w-8 h-4 rounded-full transition-colors relative ${mt5Status.auto_trading ? 'bg-green-500' : 'bg-gray-600'}`}
                                >
                                    <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform duration-300 ${mt5Status.auto_trading ? 'translate-x-4' : 'translate-x-0'}`} />
                                </button>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Symbol</label>
                                    <div className="relative">
                                        <Combobox value={manualSymbol} onChange={setManualSymbol}>
                                            <div className="relative w-full cursor-default overflow-hidden rounded-lg bg-black/20 text-left border border-white/10 focus-within:border-spidy-primary/50 focus-within:ring-1 focus-within:ring-spidy-primary/50 sm:text-sm">
                                                <Combobox.Input
                                                    className="w-full border-none py-2 pl-3 pr-10 text-xs font-mono leading-5 text-white bg-transparent focus:ring-0 focus:outline-none uppercase"
                                                    onChange={(event) => setQuery(event.target.value)}
                                                    displayValue={(person) => person}
                                                />
                                                <Combobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
                                                    <ChevronDown
                                                        className="h-4 w-4 text-gray-400"
                                                        aria-hidden="true"
                                                    />
                                                </Combobox.Button>
                                            </div>
                                            <AnimatePresence>
                                                <Combobox.Options className="absolute mt-1 max-h-60 w-full overflow-auto rounded-md bg-gray-900 border border-white/20 py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm z-[100] scrollbar-thin scrollbar-thumb-gray-700">
                                                    {filteredSymbols.length === 0 && query !== '' ? (
                                                        <div className="relative cursor-default select-none py-2 px-4 text-gray-400 text-xs font-mono">
                                                            Nothing found.
                                                        </div>
                                                    ) : (
                                                        filteredSymbols.slice(0, 50).map((s) => (
                                                            <Combobox.Option
                                                                key={s}
                                                                className={({ active }) =>
                                                                    `relative cursor-default select-none py-2 pl-10 pr-4 ${active ? 'bg-spidy-primary/20 text-white' : 'text-gray-300'
                                                                    }`
                                                                }
                                                                value={s}
                                                            >
                                                                {({ selected, active }) => (
                                                                    <>
                                                                        <span
                                                                            className={`block truncate font-mono text-xs ${selected ? 'font-bold text-spidy-primary' : 'font-normal'
                                                                                }`}
                                                                        >
                                                                            {s}
                                                                        </span>
                                                                        {selected ? (
                                                                            <span
                                                                                className={`absolute inset-y-0 left-0 flex items-center pl-3 ${active ? 'text-white' : 'text-spidy-primary'
                                                                                    }`}
                                                                            >
                                                                                <Check className="h-3 w-3" aria-hidden="true" />
                                                                            </span>
                                                                        ) : null}
                                                                    </>
                                                                )}
                                                            </Combobox.Option>
                                                        ))
                                                    )}
                                                </Combobox.Options>
                                            </AnimatePresence>
                                        </Combobox>
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Volume</label>
                                    <input
                                        type="number"
                                        value={manualVolume}
                                        onChange={(e) => setManualVolume(e.target.value)}
                                        step="0.01"
                                        className="bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-spidy-primary/50 text-center"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3 mt-1">
                                <button
                                    onClick={() => handleManualTrade('BUY')}
                                    disabled={loading}
                                    className="bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 text-green-400 py-2.5 rounded-lg text-sm font-bold transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    <TrendingUp size={14} />
                                    BUY
                                </button>
                                <button
                                    onClick={() => handleManualTrade('SELL')}
                                    disabled={loading}
                                    className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 py-2.5 rounded-lg text-sm font-bold transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    <TrendingDown size={14} />
                                    SELL
                                </button>
                            </div>
                        </div>

                        {/* AUTO-SECURE SECTION */}
                        <div className="border-t border-white/10 pt-3 flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                                    <ShieldCheck size={12} className={autoSecureEnabled ? "text-green-400" : "text-gray-600"} />
                                    Auto-Secure Profit
                                </label>
                                <button
                                    onClick={() => handleUpdateSecure(!autoSecureEnabled, undefined)}
                                    disabled={savingSecure}
                                    className={`w-8 h-4 rounded-full transition-colors relative ${autoSecureEnabled ? 'bg-green-500' : 'bg-gray-600'}`}
                                >
                                    <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform duration-300 ${autoSecureEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                                </button>
                            </div>

                            <div className="flex items-center gap-2">
                                <div className="relative flex-1">
                                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                                    <input
                                        type="number"
                                        value={secureThreshold}
                                        onChange={(e) => setSecureThreshold(e.target.value)}
                                        onBlur={(e) => handleUpdateSecure(undefined, e.target.value)}
                                        className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-5 pr-2 text-xs font-mono text-white focus:outline-none focus:border-green-500/50"
                                        placeholder="10.00"
                                    />
                                </div>
                                <button
                                    onClick={handleSecureNow}
                                    className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all active:scale-95 whitespace-nowrap flex items-center gap-1"
                                >
                                    <DollarSign size={12} />
                                    Secure Now
                                </button>
                            </div>
                        </div>
                    </motion.div>

                    {/* SECURITY MATRIX (Fixed) */}
                    {/* SECURITY MATRIX (Fixed) */}
                    <div className="flex-shrink-0 grid grid-cols-2 gap-3">
                        <SecurityItem
                            label="System"
                            status={mt5Status.connected ? "ONLINE" : "OFFLINE"}
                            icon={<Activity size={14} />}
                            color={mt5Status.connected ? "text-green-400" : "text-red-400"}
                            details={{
                                "Uptime": "Real-Time",
                                "Backend": "Active",
                                "MT5": mt5Status.connected ? "Linked" : "Missing"
                            }}
                        />
                        <SecurityItem
                            label="Latency"
                            status={`${mt5Status.latency !== undefined ? mt5Status.latency : '--'}ms`}
                            icon={<Zap size={14} />}
                            color={mt5Status.latency > 100 ? "text-red-400" : "text-yellow-400"}
                            details={{
                                "Broker": `${mt5Status.latency || 0}ms`,
                                "Loss": mt5Status.connected ? "0%" : "100%",
                                "Ping": "Real-Time"
                            }}
                        />
                    </div>

                    {/* Terminal Window (Scrollable, Flex-1) */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4 }}
                        className="bg-black/80 backdrop-blur-xl rounded-2xl border border-gray-800 p-0 flex flex-col flex-1 overflow-hidden min-h-0 shadow-2xl"
                    >
                        <div className="p-3 bg-gray-900/50 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
                            <div className="flex items-center gap-2">
                                <div className="flex gap-1.5 mr-2">
                                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
                                </div>
                                <Clock size={14} className="text-gray-500" />
                                <span className="font-mono text-xs font-bold text-gray-400 tracking-wider">SYSTEM_LOGS.sh</span>
                                <button
                                    onClick={() => window.open('http://localhost:8000/logs/download', '_blank')}
                                    className="ml-2 hover:bg-white/10 p-1 rounded transition-colors"
                                    title="Download Full Logs"
                                >
                                    <Download size={14} className="text-gray-500 hover:text-white" />
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1.5 scrollbar-thin scrollbar-thumb-gray-700 hover:scrollbar-thumb-gray-500">
                            {logs.length === 0 && <p className="text-gray-600 italic opacity-50">Waiting for system events...</p>}
                            {logs.map((log, i) => (
                                <div key={i} className="break-words leading-relaxed">
                                    <span className="text-gray-600 select-none mr-2">$</span>
                                    <span className={
                                        log.includes("ERROR") ? "text-red-400 font-bold" :
                                            log.includes("SUCCESS") ? "text-green-400 font-bold" :
                                                log.includes("TRADE") ? "text-yellow-400" :
                                                    log.includes("AUTO-TRADER") ? "text-purple-400 text-opacity-80" :
                                                        log.includes("ANALYSIS") ? "text-blue-400 font-bold" :
                                                            "text-gray-300"
                                    }>
                                        {log}
                                    </span>
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </div>
                    </motion.div>

                </div>
            </div>
        </div>
    );
}

function SecurityItem({ label, status, icon, color, details }) {
    const [isOpen, setIsOpen] = useState(false);

    // Auto-close after 4 seconds
    React.useEffect(() => {
        let timer;
        if (isOpen) {
            timer = setTimeout(() => {
                setIsOpen(false);
            }, 4000);
        }
        return () => clearTimeout(timer);
    }, [isOpen]);

    return (
        <motion.div
            layout
            onClick={() => setIsOpen(!isOpen)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`relative bg-white/5 border ${isOpen ? 'border-spidy-primary/50 bg-white/10 z-50' : 'border-white/5 z-0'} rounded-lg p-3 flex items-center justify-between transition-all cursor-pointer select-none`}
        >
            <div className={`p-1.5 rounded-md bg-black/20 ${color}`}>
                {icon}
            </div>
            <div className="flex flex-col items-end">
                <span className={`text-[10px] font-bold uppercase transition-colors ${isOpen ? 'text-spidy-primary' : 'text-gray-500'}`}>{label}</span>
                <span className="text-xs font-mono font-bold text-gray-200">{status}</span>
            </div>

            {/* Cyberpunk Tooltip (Click-activated) */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.9 }}
                        transition={{ duration: 0.2 }}
                        className="absolute bottom-full right-0 mb-2 w-56 z-50"
                        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
                    >
                        <div className="bg-black border border-spidy-primary text-white text-[10px] p-3 rounded shadow-2xl shadow-black/80 backdrop-blur-md">
                            <div className="flex justify-between border-b border-gray-800 pb-2 mb-2">
                                <span className="font-bold uppercase text-spidy-primary">{label}.DIAG</span>
                                <span className="font-mono text-green-400">● LIVE</span>
                            </div>
                            <div className="space-y-2 font-mono text-gray-300">
                                {details && Object.entries(details).map(([key, value]) => (
                                    <div key={key} className="flex justify-between items-center bg-gray-900 px-2 py-1.5 rounded border border-gray-800">
                                        <span className="uppercase opacity-70 text-[9px] min-w-[60px]">{key}:</span>
                                        <span className="text-white font-bold ml-2 truncate">{value}</span>
                                    </div>
                                ))}
                                <p className="text-[9px] italic text-gray-600 text-right mt-1 pt-1 border-t border-gray-800">System Verified</p>
                            </div>
                            {/* Close hint */}
                            <div className="text-center mt-2">
                                <button
                                    onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}
                                    className="text-[9px] text-gray-500 hover:text-white uppercase tracking-wider hover:bg-white/10 px-2 py-1 rounded transition-colors"
                                >
                                    [ Close ]
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

function StatCard({ label, value, icon, highlight, valueColor, borderColor, glow, active, delay }) {
    return (
        <motion.div
            variants={animeAppear}
            initial="hidden"
            animate="visible"
            whileHover={animeHover}
            custom={delay}
            className={`relative overflow-hidden bg-gradient-to-br from-white/10 to-white/5 p-6 rounded-2xl border ${borderColor || 'border-white/10'} shadow-lg ${glow || ''} cursor-default`}
        >
            <div className="absolute top-0 right-0 p-4 opacity-10 scale-150 transform translate-x-1/4 -translate-y-1/4">
                {icon}
            </div>

            <div className="relative z-10 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-gray-400 text-sm font-medium uppercase tracking-wider">
                    {icon && React.cloneElement(icon, { size: 16 })}
                    {label}
                </div>
                <div className={`text-3xl font-bold font-mono tracking-tight ${active ? (valueColor || (highlight ? 'text-spidy-primary' : 'text-white')) : 'text-gray-600'}`}>
                    {value}
                </div>
            </div>
        </motion.div>
    );
}
