import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity, Shield, Wallet, TrendingUp, TrendingDown, DollarSign,
    Clock, Hash, Lock, ShieldCheck, Zap, Check, ChevronDown,
    Download, X, RefreshCw, BarChart2, Target, AlertTriangle,
    ArrowUpRight, ArrowDownRight, Crosshair, Settings, BookOpen,
} from 'lucide-react';
import { Combobox } from '@headlessui/react';
import axios from 'axios';
import MarketIntelligence from './MarketIntelligence';

const API = 'http://localhost:8000';

// ── Animation Variants ────────────────────────────────────────────────────────
const fadeIn = {
    hidden: { opacity: 0, scale: 0.95, filter: 'blur(6px)' },
    visible: { opacity: 1, scale: 1, filter: 'blur(0px)', transition: { type: 'spring', stiffness: 280, damping: 22 } },
    exit: { opacity: 0, scale: 0.9, filter: 'blur(4px)' },
};

// ── Live Ticker Tape ──────────────────────────────────────────────────────────
function TickerTape({ positions, mt5Status }) {
    const tickerRef = useRef(null);
    const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US30', 'BTCUSD', 'NAS100', 'WTI'];

    // Build ticker items from live positions + defaults
    const liveMap = {};
    (positions || []).forEach(p => { liveMap[p.symbol] = p; });

    const items = SYMBOLS.map(sym => ({
        symbol: sym,
        price: liveMap[sym]?.price || null,
        profit: liveMap[sym]?.profit || null,
        isOpen: !!liveMap[sym],
    }));
    const doubled = [...items, ...items]; // Infinite scroll trick

    return (
        <div className="w-full bg-black/60 border-b border-white/5 py-1.5 overflow-hidden relative flex-shrink-0">
            <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-black/80 to-transparent z-10 pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-black/80 to-transparent z-10 pointer-events-none" />
            <motion.div
                ref={tickerRef}
                className="flex gap-8 whitespace-nowrap"
                animate={{ x: [0, -1200] }}
                transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
            >
                {doubled.map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs font-mono flex-shrink-0">
                        <span className={`font-bold ${item.isOpen ? 'text-spidy-primary' : 'text-gray-400'}`}>
                            {item.symbol}
                        </span>
                        {item.price ? (
                            <span className="text-white">{parseFloat(item.price).toFixed(item.symbol.includes('JPY') ? 3 : 5)}</span>
                        ) : (
                            <span className="text-gray-600">−−−−−</span>
                        )}
                        {item.profit !== null && (
                            <span className={`text-[9px] font-bold px-1 rounded ${item.profit >= 0 ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                {item.profit >= 0 ? '+' : ''}{item.profit.toFixed(2)}
                            </span>
                        )}
                        <span className="text-white/10">│</span>
                    </div>
                ))}
            </motion.div>
        </div>
    );
}

// ── Analytics Bar ─────────────────────────────────────────────────────────────
function AnalyticsBar() {
    const [analytics, setAnalytics] = useState(null);

    useEffect(() => {
        const fetch = async () => {
            try { const r = await axios.get(`${API}/analytics`, { timeout: 4000 }); setAnalytics(r.data); }
            catch (e) { /* silent */ }
        };
        fetch();
        const i = setInterval(fetch, 15000);
        return () => clearInterval(i);
    }, []);

    if (!analytics?.today) return null;
    const t = analytics.today;

    return (
        <div className="w-full bg-black/40 border-b border-white/5 px-4 py-1.5 flex items-center gap-6 text-[10px] font-mono text-gray-500 overflow-x-auto flex-shrink-0">
            <span className="text-gray-600 font-bold uppercase tracking-widest">Today</span>
            <div className="flex items-center gap-1">
                <span>Trades:</span>
                <span className="text-white font-bold">{t.total_trades}</span>
            </div>
            <div className="flex items-center gap-1">
                <span>Win Rate:</span>
                <span className={`font-bold ${t.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>{t.win_rate}%</span>
            </div>
            <div className="flex items-center gap-1">
                <span>Avg Win:</span>
                <span className="text-green-400 font-bold">+${t.avg_profit}</span>
            </div>
            <div className="flex items-center gap-1">
                <span>Avg Loss:</span>
                <span className="text-red-400 font-bold">${t.avg_loss}</span>
            </div>
            <div className="flex items-center gap-1">
                <span>Daily PnL:</span>
                <span className={`font-black ${t.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.daily_pnl >= 0 ? '+' : ''}${t.daily_pnl}
                </span>
            </div>
        </div>
    );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, icon, valueColor, borderColor, glow, highlight, active, delay = 0 }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, type: 'spring' }}
            className={`relative overflow-hidden bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-md rounded-2xl border ${borderColor || 'border-white/10'} p-5 shadow-xl ${glow ? `shadow-${glow}` : ''} ${highlight ? 'ring-1 ring-white/10' : ''}`}
        >
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-gray-400 uppercase tracking-widest font-bold">{label}</span>
                <div className={`p-2 rounded-lg ${active ? 'bg-white/10' : 'bg-white/5'}`}>{icon}</div>
            </div>
            <p className={`text-2xl font-black font-mono ${valueColor || 'text-white'}`}>{value}</p>
            <div className="absolute bottom-0 right-0 w-20 h-20 bg-white/2 rounded-full blur-2xl pointer-events-none" />
        </motion.div>
    );
}

// ── Trade Details Modal ────────────────────────────────────────────────────────
function TradeDetailsModal({ trade, onClose }) {
    if (!trade) return null;
    const profit = parseFloat(trade.profit);
    const profitColor = profit >= 0 ? 'text-green-400' : 'text-red-400';
    const entryPrice = parseFloat(trade.open_price);
    const exitPrice = parseFloat(trade.close_price);
    let pctChange = entryPrice > 0 ? ((exitPrice - entryPrice) / entryPrice) * 100 : 0;
    if (trade.type === 'SELL') pctChange *= -1;

    let durationStr = 'N/A';
    if (trade.open_time && trade.close_time) {
        const ms = new Date(trade.close_time) - new Date(trade.open_time);
        if (!isNaN(ms)) {
            const h = Math.floor(ms / 3600000);
            const m = Math.floor((ms % 3600000) / 60000);
            durationStr = `${h}h ${m}m`;
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose}>
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                className="bg-gray-900 border border-white/10 rounded-2xl shadow-2xl p-6 max-w-sm w-full relative"
                onClick={e => e.stopPropagation()}>
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            {trade.symbol}
                            <span className={`text-xs px-2 py-0.5 rounded ${trade.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{trade.type}</span>
                        </h3>
                        <p className="text-xs text-gray-500 font-mono">#{trade.ticket}</p>
                    </div>
                    <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-full"><X size={18} className="text-gray-400" /></button>
                </div>
                <div className="bg-white/5 p-4 rounded-xl mb-4 flex justify-between items-center">
                    <div>
                        <p className="text-xs text-gray-400 uppercase">Net Profit</p>
                        <p className={`text-2xl font-black font-mono ${profitColor}`}>{profit >= 0 ? '+' : ''}{profit.toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                        <p className={`text-sm font-mono font-bold ${pctChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pctChange >= 0 ? '▲' : '▼'} {Math.abs(pctChange).toFixed(3)}%
                        </p>
                        <p className="text-[10px] text-gray-500">Duration: {durationStr}</p>
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-black/20 p-3 rounded-lg"><p className="text-[10px] text-gray-500 uppercase">Entry</p><p className="font-mono text-gray-200">{trade.open_price}</p></div>
                    <div className="bg-black/20 p-3 rounded-lg text-right"><p className="text-[10px] text-gray-500 uppercase">Exit</p><p className="font-mono text-gray-200">{trade.close_price}</p></div>
                </div>
            </motion.div>
        </div>
    );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function TradingDashboard({ mt5Status, logs, logsEndRef }) {
    const [manualSymbol, setManualSymbol] = useState('EURUSD');
    const [manualVolume, setManualVolume] = useState('0.01');
    const [manualSL, setManualSL] = useState('');
    const [manualTP, setManualTP] = useState('');
    const [loading, setLoading] = useState(false);
    const [availableSymbols, setAvailableSymbols] = useState([]);
    const [query, setQuery] = useState('');
    const [selectedTrade, setSelectedTrade] = useState(null);
    const [showHistory, setShowHistory] = useState(false);
    const [tradeHistory, setTradeHistory] = useState([]);
    const [sortConfig, setSortConfig] = useState({ key: 'time', direction: 'desc' });
    const [autoSecureEnabled, setAutoSecureEnabled] = useState(false);
    const [secureThreshold, setSecureThreshold] = useState('10.0');
    const [savingSecure, setSavingSecure] = useState(false);
    const [activeRiskPct, setActiveRiskPct] = useState('1.0');
    const [tradeMode, setTradeMode] = useState('simple'); // 'simple' | 'advanced'
    const [sessionId] = useState(Math.random().toString(36).substring(7).toUpperCase());

    const filteredSymbols = query === ''
        ? availableSymbols
        : availableSymbols.filter(s => s.toLowerCase().includes(query.toLowerCase()));

    // Risk calc: USD at risk based on account %
    const calcRiskUSD = () => {
        const bal = parseFloat(mt5Status?.balance) || 0;
        const pct = parseFloat(activeRiskPct) || 1;
        return ((bal * pct) / 100).toFixed(2);
    };

    const handleSort = key => setSortConfig(prev => ({
        key, direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));

    const getSortedPositions = () => {
        if (!mt5Status?.positions) return [];
        return [...mt5Status.positions].sort((a, b) => {
            let vA = a[sortConfig.key], vB = b[sortConfig.key];
            if (['profit', 'volume', 'price'].includes(sortConfig.key)) { vA = parseFloat(vA); vB = parseFloat(vB); }
            if (vA < vB) return sortConfig.direction === 'asc' ? -1 : 1;
            if (vA > vB) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
    };

    useEffect(() => {
        const fetchSymbols = async (retries = 5) => {
            try {
                const r = await axios.get(`${API}/symbols`);
                if (r.data?.symbols) setAvailableSymbols(r.data.symbols);
            } catch {
                if (retries > 0) setTimeout(() => fetchSymbols(retries - 1), 3000);
            }
        };
        const fetchSettings = async () => {
            try {
                const r = await axios.get(`${API}/status`);
                if (r.data?.risk_settings?.auto_secure) {
                    const c = r.data.risk_settings.auto_secure;
                    setAutoSecureEnabled(c.enabled);
                    setSecureThreshold(c.threshold);
                }
            } catch { /* silent */ }
        };
        const fetchHistory = async () => {
            try {
                const r = await axios.get(`${API}/history`);
                if (r.data?.history) setTradeHistory(r.data.history);
            } catch { /* silent */ }
        };
        fetchSymbols(); fetchSettings(); fetchHistory();
        const i = setInterval(() => { fetchHistory(); fetchSettings(); }, 10000);
        return () => clearInterval(i);
    }, []);

    const isProfitable = parseFloat(mt5Status?.profit) >= 0;

    const handleManualTrade = async (action) => {
        setLoading(true);
        try {
            await axios.post(`${API}/trade`, {
                action, symbol: manualSymbol, volume: manualVolume,
            });
        } catch (e) { console.error('Trade Failed', e); }
        setLoading(false);
    };

    const toggleAutoTrading = async () => {
        try { await axios.post(`${API}/toggle_auto`, { enable: !mt5Status?.auto_trading }); }
        catch (e) { console.error('Toggle Failed', e); }
    };

    const handleCloseTrade = async (pos) => {
        if (!confirm(`Close ${pos.symbol} (#${pos.ticket})?`)) return;
        try { await axios.post(`${API}/close_trade`, { ticket: pos.ticket, symbol: pos.symbol }); }
        catch (e) { alert('Close failed: ' + e.message); }
    };

    const handleCloseAllLosses = async () => {
        if (!confirm('Close ALL losing positions now?')) return;
        try {
            await axios.post(`${API}/close_all_trades`, { profitable_only: false });
        } catch (e) { alert('Failed: ' + e.message); }
    };

    const handleCloseAllProfits = async () => {
        if (!confirm('Secure ALL profitable positions now?')) return;
        try {
            await axios.post(`${API}/close_all_trades`, { profitable_only: true, threshold: 0.0 });
        } catch (e) { alert('Failed: ' + e.message); }
    };

    const handleUpdateSecure = async (newEnabled, newThreshold) => {
        setSavingSecure(true);
        try {
            const payload = {};
            if (newEnabled !== undefined) payload.enabled = newEnabled;
            if (newThreshold !== undefined) payload.threshold = parseFloat(newThreshold);
            const r = await axios.post(`${API}/settings/auto_secure`, payload);
            if (r.data.status === 'UPDATED') {
                if (newEnabled !== undefined) setAutoSecureEnabled(newEnabled);
                if (newThreshold !== undefined) setSecureThreshold(newThreshold);
            }
        } catch { /* silent */ }
        setSavingSecure(false);
    };

    const getPositionDuration = (time) => {
        if (!time) return '—';
        const ms = Date.now() - new Date(time).getTime();
        if (isNaN(ms)) return '—';
        const h = Math.floor(ms / 3600000);
        const m = Math.floor((ms % 3600000) / 60000);
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
    };

    return (
        <div className="flex flex-col gap-0 h-full overflow-hidden relative">
            <TradeDetailsModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />

            {/* Ticker Tape */}
            <TickerTape positions={mt5Status?.positions} mt5Status={mt5Status} />

            {/* Analytics Bar */}
            <AnalyticsBar />

            {/* Account Stats */}
            <div className="grid grid-cols-3 gap-4 p-4 pb-2 flex-shrink-0">
                <StatCard
                    label="Balance" delay={0}
                    value={`$${typeof mt5Status?.balance === 'number' ? mt5Status.balance.toFixed(2) : '0.00'}`}
                    icon={<Wallet size={20} className="text-blue-400" />}
                    active={mt5Status?.connected}
                />
                <StatCard
                    label="Equity" delay={0.05} highlight
                    value={`$${typeof mt5Status?.equity === 'number' ? mt5Status.equity.toFixed(2) : '0.00'}`}
                    icon={<DollarSign size={20} className="text-purple-400" />}
                    active={mt5Status?.connected}
                />
                <StatCard
                    label="Open P/L" delay={0.1}
                    value={`$${typeof mt5Status?.profit === 'number' ? mt5Status.profit.toFixed(2) : '0.00'}`}
                    icon={isProfitable ? <TrendingUp size={20} className="text-green-400" /> : <TrendingDown size={20} className="text-red-400" />}
                    valueColor={isProfitable ? 'text-green-400' : 'text-red-400'}
                    borderColor={isProfitable ? 'border-green-500/20' : 'border-red-500/20'}
                    active={mt5Status?.connected}
                />
            </div>

            {/* Main Layout */}
            <div className="flex flex-1 gap-4 px-4 pb-4 min-h-0 overflow-hidden">

                {/* LEFT: Positions + History */}
                <motion.div
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
                    className="flex-1 bg-gradient-to-b from-white/10 to-white/5 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden flex flex-col shadow-xl min-w-0"
                >
                    {/* Status Banner */}
                    <div className="flex-shrink-0 border-b border-white/10">
                        {!mt5Status?.connected ? (
                            <div className="w-full bg-red-500/20 py-3 flex items-center justify-center gap-2 animate-pulse">
                                <ShieldCheck size={18} className="text-red-500" />
                                <span className="text-sm font-black text-red-500 uppercase tracking-widest">CONNECTION LOST</span>
                            </div>
                        ) : mt5Status?.market_status === 'ALGO_DISABLED' ? (
                            <div className="w-full bg-red-500/20 py-3 flex flex-col items-center justify-center animate-pulse border-b border-red-500/30">
                                <div className="flex items-center gap-2"><Lock size={18} className="text-red-500" /><span className="text-sm font-black text-red-500 uppercase">PERMISSION DENIED</span></div>
                                <p className="text-[9px] text-red-400 font-bold uppercase mt-0.5">Enable Algo Trading in MT5</p>
                            </div>
                        ) : mt5Status?.market_status === 'CLOSED_WEEKEND' ? (
                            <div className="w-full bg-yellow-500/10 py-3 flex items-center justify-center gap-2 border-b border-yellow-500/20">
                                <Clock size={18} className="text-yellow-500" />
                                <span className="text-sm font-black text-yellow-500 uppercase">MARKET CLOSED — WEEKEND</span>
                            </div>
                        ) : mt5Status?.auto_trading ? (
                            <div className="w-full bg-green-500/10 py-2.5 flex items-center justify-center gap-2 border-b border-green-500/20">
                                <Activity size={16} className="text-green-500 animate-pulse" />
                                <span className="text-sm font-black text-green-500 uppercase tracking-widest">AUTO-TRADER ACTIVE</span>
                                <span className="text-[9px] text-green-600 font-bold ml-2">{mt5Status?.market_status || 'MARKET OPEN'} • {mt5Status?.server_time}</span>
                            </div>
                        ) : (
                            <div className="w-full bg-blue-500/10 py-2.5 flex items-center justify-center gap-2 border-b border-blue-500/20">
                                <Hash size={16} className="text-blue-400" />
                                <span className="text-sm font-black text-blue-400 uppercase tracking-widest">MANUAL MODE</span>
                                <span className="text-[9px] text-blue-400/70 font-bold ml-2">{mt5Status?.server_time}</span>
                            </div>
                        )}
                    </div>

                    {/* Macro Status Row */}
                    {mt5Status?.connected && (
                        <div className="flex-shrink-0 bg-black/40 border-b border-white/5 py-1.5 px-4 flex items-center justify-between text-[9px] font-mono font-bold tracking-widest uppercase text-gray-500">
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-gray-600">SENTIMENT:</span>
                                    <span className={mt5Status?.sentiment === 'BULLISH' ? 'text-green-400' : mt5Status?.sentiment === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}>
                                        {mt5Status?.sentiment || 'NEUTRAL'}
                                    </span>
                                </div>
                                {mt5Status?.oil?.symbol && (
                                    <div className="flex items-center gap-1.5 border-l border-white/10 pl-4">
                                        <span className="text-gray-600">OIL:</span>
                                        <span className={mt5Status.oil.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                                            {mt5Status.oil.symbol} {mt5Status.oil.change_pct > 0 ? '+' : ''}{parseFloat(mt5Status.oil.change_pct).toFixed(2)}%
                                        </span>
                                    </div>
                                )}
                                {mt5Status?.dxy?.status && (
                                    <div className="flex items-center gap-1.5 border-l border-white/10 pl-4">
                                        <span className="text-gray-600">DXY:</span>
                                        <span className={mt5Status.dxy.status === 'BULLISH' ? 'text-green-400' : mt5Status.dxy.status === 'BEARISH' ? 'text-red-400' : 'text-yellow-400'}>
                                            {mt5Status.dxy.status}
                                        </span>
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-1.5">
                                <span className="text-gray-600">RISK:</span>
                                <span className="text-spidy-primary">{mt5Status?.risk_settings?.mode || 'STANDARD'}</span>
                                <span className="border-l border-white/10 pl-3 text-gray-600">LATENCY:</span>
                                <span className="text-blue-400">{mt5Status?.latency || '--'}ms</span>
                            </div>
                        </div>
                    )}

                    {/* Tabs */}
                    <div className="flex border-b border-white/10 flex-shrink-0">
                        <button
                            onClick={() => setShowHistory(false)}
                            className={`flex-1 py-3 flex justify-center items-center gap-2 text-xs font-bold tracking-wide transition-colors ${!showHistory ? 'bg-white/10 text-spidy-primary border-b-2 border-spidy-primary' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Activity size={14} /> ACTIVE POSITIONS
                            {mt5Status?.positions?.length > 0 && (
                                <span className="bg-spidy-primary text-white text-[9px] font-black px-1.5 py-0.5 rounded-full min-w-[16px] text-center">
                                    {mt5Status.positions.length}
                                </span>
                            )}
                        </button>
                        <button
                            onClick={() => setShowHistory(true)}
                            className={`flex-1 py-3 flex justify-center items-center gap-2 text-xs font-bold tracking-wide transition-colors ${showHistory ? 'bg-white/10 text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:bg-white/5'}`}
                        >
                            <Clock size={14} /> HISTORY
                        </button>
                    </div>

                    {/* Table Area */}
                    <div className="flex-1 overflow-auto">
                        {!showHistory ? (
                            /* ACTIVE POSITIONS TABLE */
                            <table className="w-full text-left text-xs text-gray-400 border-separate border-spacing-y-0.5">
                                <thead className="sticky top-0 bg-black/60 backdrop-blur-sm z-10">
                                    <tr className="text-[9px] uppercase font-bold text-gray-600 tracking-wider">
                                        <th className="px-3 py-2 cursor-pointer hover:text-white" onClick={() => handleSort('symbol')}>Symbol</th>
                                        <th className="px-3 py-2">Side</th>
                                        <th className="px-3 py-2 cursor-pointer hover:text-white" onClick={() => handleSort('volume')}>Size</th>
                                        <th className="px-3 py-2">Entry</th>
                                        <th className="px-3 py-2">Duration</th>
                                        <th className="px-3 py-2 text-center text-yellow-500/70">ROI%</th>
                                        <th className="px-3 py-2 text-right cursor-pointer hover:text-white" onClick={() => handleSort('profit')}>P/L</th>
                                        <th className="px-3 py-2 text-center">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <AnimatePresence>
                                        {mt5Status?.positions?.length > 0 ? (
                                            getSortedPositions().map((pos) => {
                                                // Use the synchronized ROI from the backend
                                                const roi = pos.roi || 0;
                                                const duration = getPositionDuration(pos.time);
                                                return (
                                                    <motion.tr
                                                        key={pos.ticket}
                                                        variants={fadeIn} initial="hidden" animate="visible" exit="exit" layout
                                                        className="bg-white/5 hover:bg-white/10 transition-colors group"
                                                    >
                                                        <td className="px-3 py-2.5 font-bold text-white rounded-l-xl border-l-2 border-transparent group-hover:border-spidy-primary transition-all">
                                                            {pos.symbol}
                                                        </td>
                                                        <td className="px-3 py-2.5">
                                                            <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase ${pos.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                                {pos.type === 'BUY' ? <ArrowUpRight size={10} className="inline mb-0.5" /> : <ArrowDownRight size={10} className="inline mb-0.5" />} {pos.type}
                                                            </span>
                                                        </td>
                                                        <td className="px-3 py-2.5 font-mono text-gray-300">{pos.volume}</td>
                                                        <td className="px-3 py-2.5 font-mono text-gray-400">{parseFloat(pos.price).toFixed(pos.symbol?.includes('JPY') ? 3 : 5)}</td>
                                                        <td className="px-3 py-2.5 font-mono text-gray-500 text-[9px]">{duration}</td>
                                                        <td className="px-3 py-2.5 text-center">
                                                            <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${roi >= 0 ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                                                {roi >= 0 ? '+' : ''}{roi.toFixed(2)}%
                                                            </span>
                                                        </td>
                                                        <td className={`px-3 py-2.5 font-mono font-bold text-right ${pos.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            <div className="flex flex-col items-end gap-0.5">
                                                                <span>{pos.profit >= 0 ? '+' : ''}{pos.profit.toFixed(2)}</span>
                                                                <div className="w-10 h-0.5 bg-white/5 rounded-full overflow-hidden">
                                                                    <div className={`h-full rounded-full ${pos.profit >= 0 ? 'bg-green-400' : 'bg-red-400'}`}
                                                                        style={{ width: `${Math.min(Math.abs(roi) * 10, 100)}%` }} />
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="px-3 py-2.5 text-center rounded-r-xl">
                                                            <button
                                                                onClick={() => handleCloseTrade(pos)}
                                                                className="text-[9px] bg-red-500/20 hover:bg-red-500/40 text-red-300 border border-red-500/30 px-2 py-1 rounded transition-colors font-bold"
                                                            >
                                                                ✕ Close
                                                            </button>
                                                        </td>
                                                    </motion.tr>
                                                );
                                            })
                                        ) : (
                                            <tr>
                                                <td colSpan="8" className="p-12 text-center">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center">
                                                            <Crosshair className="text-gray-600" size={28} />
                                                        </div>
                                                        <p className="text-gray-500 font-medium">No Active Positions</p>
                                                        <p className="text-xs text-gray-600">Spidy AI is scanning for signals...</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        ) : (
                            /* HISTORY TABLE */
                            <table className="w-full text-left text-xs text-gray-400 border-separate border-spacing-y-0.5">
                                <thead className="sticky top-0 bg-black/60 backdrop-blur-sm z-10">
                                    <tr className="text-[9px] uppercase font-bold text-gray-600 tracking-wider">
                                        <th className="px-3 py-2">Symbol</th>
                                        <th className="px-3 py-2">Side</th>
                                        <th className="px-3 py-2">Size</th>
                                        <th className="px-3 py-2">Closed</th>
                                        <th className="px-3 py-2">Entry → Exit</th>
                                        <th className="px-3 py-2 text-right">Profit</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <AnimatePresence>
                                        {tradeHistory?.length > 0 ? (
                                            tradeHistory.map((deal, i) => (
                                                <motion.tr
                                                    key={deal.ticket || i}
                                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                                    className="bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                                                    onClick={() => setSelectedTrade(deal)}
                                                >
                                                    <td className="px-3 py-2.5 font-bold text-gray-300 rounded-l-xl">{deal.symbol}</td>
                                                    <td className="px-3 py-2.5">
                                                        <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase ${deal.type === 'BUY' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                                                            {deal.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2.5 font-mono text-gray-500">{deal.volume}</td>
                                                    <td className="px-3 py-2.5 font-mono text-gray-400 text-[9px]">
                                                        {deal.close_time?.split(' ')[0] || '—'}
                                                    </td>
                                                    <td className="px-3 py-2.5 font-mono text-gray-500 text-[9px]">
                                                        {deal.open_price} → {deal.close_price || '—'}
                                                    </td>
                                                    <td className={`px-3 py-2.5 font-mono font-bold text-right rounded-r-xl ${deal.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {deal.profit >= 0 ? '+' : ''}{parseFloat(deal.profit || 0).toFixed(2)}
                                                    </td>
                                                </motion.tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="6" className="p-12 text-center">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center">
                                                            <BookOpen className="text-gray-600" size={28} />
                                                        </div>
                                                        <p className="text-gray-500">No History Available</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Quick Actions Bar */}
                    <div className="flex-shrink-0 border-t border-white/10 p-3 flex items-center gap-2">
                        <button
                            onClick={handleCloseAllProfits}
                            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-green-500/15 hover:bg-green-500/25 text-green-400 border border-green-500/25 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all"
                        >
                            <TrendingUp size={12} /> Close Profits
                        </button>
                        <button
                            onClick={handleCloseAllLosses}
                            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/25 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all"
                        >
                            <TrendingDown size={12} /> Close Losses
                        </button>
                        <button
                            onClick={async () => {
                                if (!confirm('EMERGENCY STOP: Close ALL positions immediately?')) return;
                                try { await axios.post(`${API}/close_all_trades`, { profitable_only: false }); }
                                catch (e) { alert('Failed: ' + e.message); }
                            }}
                            className="flex items-center justify-center gap-1.5 px-4 py-2 bg-red-600/30 hover:bg-red-600/50 text-red-300 border border-red-600/40 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all"
                        >
                            <AlertTriangle size={12} /> STOP ALL
                        </button>
                    </div>
                </motion.div>

                {/* RIGHT: Controls + Market Intelligence */}
                <div className="flex flex-col gap-3 w-72 flex-shrink-0 overflow-y-auto">

                    {/* COMMAND CONSOLE */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.25 }}
                        className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-4 flex flex-col gap-3 shadow-xl flex-shrink-0"
                    >
                        {/* Header Row */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Crosshair size={14} className="text-spidy-primary" />
                                <h3 className="text-[11px] font-bold text-gray-200 tracking-widest uppercase">Trade Console</h3>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[9px] text-gray-500 uppercase font-bold">Auto</span>
                                <button
                                    onClick={toggleAutoTrading}
                                    className={`w-8 h-4 rounded-full transition-all relative ${mt5Status?.auto_trading ? 'bg-green-500' : 'bg-gray-600'}`}
                                >
                                    <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${mt5Status?.auto_trading ? 'translate-x-4' : 'translate-x-0'}`} />
                                </button>
                            </div>
                        </div>

                        {/* Mode Toggle */}
                        <div className="flex gap-1 bg-black/30 rounded-lg p-0.5">
                            <button
                                onClick={() => setTradeMode('simple')}
                                className={`flex-1 py-1 text-[9px] font-bold uppercase rounded-md transition-all ${tradeMode === 'simple' ? 'bg-spidy-primary text-white' : 'text-gray-500 hover:text-white'}`}
                            >Simple</button>
                            <button
                                onClick={() => setTradeMode('advanced')}
                                className={`flex-1 py-1 text-[9px] font-bold uppercase rounded-md transition-all ${tradeMode === 'advanced' ? 'bg-spidy-primary text-white' : 'text-gray-500 hover:text-white'}`}
                            >Advanced</button>
                        </div>

                        {/* Symbol */}
                        <div className="flex flex-col gap-1">
                            <label className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Symbol</label>
                            <div className="relative">
                                <Combobox value={manualSymbol} onChange={setManualSymbol}>
                                    <div className="relative w-full overflow-hidden rounded-lg bg-black/30 border border-white/10 focus-within:border-spidy-primary/50">
                                        <Combobox.Input
                                            className="w-full border-none py-2 pl-3 pr-8 text-xs font-mono text-white bg-transparent focus:ring-0 focus:outline-none uppercase"
                                            onChange={e => setQuery(e.target.value)}
                                            displayValue={v => v}
                                        />
                                        <Combobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
                                            <ChevronDown className="h-3 w-3 text-gray-400" />
                                        </Combobox.Button>
                                    </div>
                                    <Combobox.Options className="absolute mt-1 max-h-48 w-full overflow-auto rounded-lg bg-gray-900 border border-white/20 py-1 text-xs shadow-xl z-[100]">
                                        {filteredSymbols.slice(0, 50).map(s => (
                                            <Combobox.Option key={s} value={s}
                                                className={({ active }) => `py-1.5 pl-3 pr-3 cursor-default font-mono ${active ? 'bg-spidy-primary/20 text-white' : 'text-gray-300'}`}
                                            >{s}</Combobox.Option>
                                        ))}
                                    </Combobox.Options>
                                </Combobox>
                            </div>
                        </div>

                        {/* Volume + Risk % */}
                        <div className="grid grid-cols-2 gap-2">
                            <div className="flex flex-col gap-1">
                                <label className="text-[9px] font-bold text-gray-500 uppercase">Volume</label>
                                <input
                                    type="number" step="0.01" min="0.01" value={manualVolume}
                                    onChange={e => setManualVolume(e.target.value)}
                                    className="w-full bg-black/30 border border-white/10 rounded-lg py-2 px-3 text-xs font-mono text-white focus:outline-none focus:border-spidy-primary/50"
                                />
                            </div>
                            <div className="flex flex-col gap-1">
                                <label className="text-[9px] font-bold text-gray-500 uppercase">Risk %</label>
                                <div className="relative">
                                    <input
                                        type="number" step="0.1" min="0.1" max="10" value={activeRiskPct}
                                        onChange={e => setActiveRiskPct(e.target.value)}
                                        className="w-full bg-black/30 border border-white/10 rounded-lg py-2 px-3 text-xs font-mono text-white focus:outline-none focus:border-spidy-primary/50"
                                    />
                                </div>
                                <p className="text-[9px] text-gray-600">≈ ${calcRiskUSD()} at risk</p>
                            </div>
                        </div>

                        {/* Advanced: SL/TP */}
                        <AnimatePresence>
                            {tradeMode === 'advanced' && (
                                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                                    className="grid grid-cols-2 gap-2 overflow-hidden">
                                    <div className="flex flex-col gap-1">
                                        <label className="text-[9px] font-bold text-red-500/70 uppercase">Stop Loss (pips)</label>
                                        <input type="number" step="1" min="0" value={manualSL}
                                            onChange={e => setManualSL(e.target.value)}
                                            placeholder="e.g. 20"
                                            className="w-full bg-red-500/5 border border-red-500/20 rounded-lg py-2 px-3 text-xs font-mono text-red-300 focus:outline-none focus:border-red-500/50 placeholder:text-gray-600"
                                        />
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <label className="text-[9px] font-bold text-green-500/70 uppercase">Take Profit (pips)</label>
                                        <input type="number" step="1" min="0" value={manualTP}
                                            onChange={e => setManualTP(e.target.value)}
                                            placeholder="e.g. 40"
                                            className="w-full bg-green-500/5 border border-green-500/20 rounded-lg py-2 px-3 text-xs font-mono text-green-300 focus:outline-none focus:border-green-500/50 placeholder:text-gray-600"
                                        />
                                    </div>
                                    {(manualSL || manualTP) && (
                                        <div className="col-span-2 bg-black/20 rounded-lg p-2 text-[9px] text-gray-500">
                                            {manualSL && <p>Risk: <span className="text-red-400">{manualSL} pips = ~${(parseFloat(manualSL || 0) * parseFloat(manualVolume || 0.01) * 10).toFixed(2)}</span></p>}
                                            {manualTP && <p>Target: <span className="text-green-400">{manualTP} pips = ~${(parseFloat(manualTP || 0) * parseFloat(manualVolume || 0.01) * 10).toFixed(2)}</span></p>}
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* BUY / SELL Buttons */}
                        <div className="grid grid-cols-2 gap-2 pt-1">
                            <motion.button
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                                onClick={() => handleManualTrade('BUY')}
                                disabled={loading}
                                className="flex items-center justify-center gap-1.5 py-3 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-lg shadow-green-900/40 transition-all disabled:opacity-50"
                            >
                                <ArrowUpRight size={14} /> BUY
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                                onClick={() => handleManualTrade('SELL')}
                                disabled={loading}
                                className="flex items-center justify-center gap-1.5 py-3 bg-gradient-to-r from-red-700 to-red-600 hover:from-red-600 hover:to-red-500 text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-lg shadow-red-900/40 transition-all disabled:opacity-50"
                            >
                                <ArrowDownRight size={14} /> SELL
                            </motion.button>
                        </div>
                    </motion.div>

                    {/* AUTO-SECURE PANEL */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}
                        className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-4 flex flex-col gap-3 flex-shrink-0"
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Shield size={14} className="text-yellow-400" />
                                <h3 className="text-[11px] font-bold text-gray-200 tracking-widest uppercase">Auto-Secure</h3>
                            </div>
                            <button
                                onClick={() => handleUpdateSecure(!autoSecureEnabled, undefined)}
                                disabled={savingSecure}
                                className={`w-8 h-4 rounded-full transition-all relative ${autoSecureEnabled ? 'bg-yellow-500' : 'bg-gray-600'}`}
                            >
                                <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${autoSecureEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                            </button>
                        </div>
                        {autoSecureEnabled && (
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-2">
                                    <label className="text-[9px] text-gray-500 uppercase font-bold flex-1">Close at $</label>
                                    <input
                                        type="number" step="0.5" min="0"
                                        value={secureThreshold}
                                        onChange={e => setSecureThreshold(e.target.value)}
                                        onBlur={() => handleUpdateSecure(undefined, secureThreshold)}
                                        className="w-24 bg-black/30 border border-white/10 rounded-lg py-1.5 px-2 text-xs font-mono text-yellow-300 focus:outline-none focus:border-yellow-500/50 text-right"
                                    />
                                </div>
                            </div>
                        )}
                    </motion.div>

                    {/* MARKET INTELLIGENCE PANEL */}
                    <MarketIntelligence />
                </div>
            </div>

            {/* SYSTEM LOG PANEL */}
            <SystemLogPanel logs={logs} logsEndRef={logsEndRef} />
        </div>
    );
}

// ── System Log Panel ──────────────────────────────────────────────────────────
function SystemLogPanel({ logs, logsEndRef }) {
    const [collapsed, setCollapsed] = useState(false);

    const getLogColor = (line) => {
        if (!line) return 'text-gray-500';
        const l = line.toLowerCase();
        if (l.includes('error') || l.includes('fail') || l.includes('❌') || l.includes('🚨')) return 'text-red-400';
        if (l.includes('warn') || l.includes('⚠️') || l.includes('hold')) return 'text-yellow-400';
        if (l.includes('success') || l.includes('✅') || l.includes('profit') || l.includes('💰') || l.includes('secured')) return 'text-green-400';
        if (l.includes('hft') || l.includes('buy') || l.includes('sell') || l.includes('📈') || l.includes('📉')) return 'text-blue-400';
        if (l.includes('info') || l.includes('🧠') || l.includes('ai')) return 'text-purple-400';
        return 'text-gray-400';
    };

    return (
        <div className={`flex-shrink-0 border-t border-white/10 bg-black/60 backdrop-blur-md transition-all duration-300 ${collapsed ? 'h-9' : 'h-44'}`}>
            {/* Log Header */}
            <div
                className="flex items-center justify-between px-4 h-9 cursor-pointer hover:bg-white/5 select-none"
                onClick={() => setCollapsed(p => !p)}
            >
                <div className="flex items-center gap-2">
                    <Activity size={12} className="text-green-400 animate-pulse" />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">System Log</span>
                    {logs?.length > 0 && (
                        <span className="text-[9px] text-gray-600 font-mono">({logs.length} entries)</span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600 uppercase font-bold">
                        {collapsed ? '▲ Expand' : '▼ Collapse'}
                    </span>
                </div>
            </div>

            {/* Log Body */}
            {!collapsed && (
                <div className="h-[calc(100%-36px)] overflow-y-auto px-4 pb-2 font-mono text-[10px] space-y-0.5 scroll-smooth">
                    {logs && logs.length > 0 ? (
                        <>
                            {logs.map((line, i) => (
                                <div key={i} className={`leading-relaxed ${getLogColor(line)} flex gap-2 items-start`}>
                                    <span className="text-gray-700 flex-shrink-0 tabular-nums">{String(i + 1).padStart(3, '0')}</span>
                                    <span className="break-all">{line}</span>
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-full">
                            <p className="text-gray-600 text-[10px]">Waiting for bridge connection...</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
