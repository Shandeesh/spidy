import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    PieChart, TrendingUp, Target, Shield, Wallet, DollarSign, Activity,
    Zap, Lock, BookOpen, Layers, Search, AlertOctagon, BrainCircuit, Calendar
} from 'lucide-react';

const SpiderSenseModule = ({ mt5Status }) => {
    // Real Data from Backend
    const analysisData = mt5Status?.analysis || {};
    const hasData = Object.keys(analysisData).length > 0;

    return (
        <div className="h-full flex flex-col gap-6 p-6">
            {/* Sentiment Header */}
            <div className="flex items-center justify-between p-4 bg-spidy-primary/10 border border-spidy-primary/30 rounded-xl relative overflow-hidden">
                <div className="absolute inset-0 bg-spidy-primary/5 animate-pulse" />
                <div className="flex items-center gap-4 relative z-10">
                    <div className="p-3 bg-spidy-primary/20 text-spidy-primary rounded-full">
                        <BrainCircuit size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white leading-none">Global Sentiment</h3>
                        <p className={`text-sm font-mono mt-1 ${mt5Status?.sentiment === 'BULLISH' ? 'text-green-400' : mt5Status?.sentiment === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}`}>
                            {mt5Status?.sentiment || 'NEUTRAL'} MARKET ({hasData ? 'LIVE' : 'WAITING'})
                        </p>
                    </div>
                </div>
                <div className="text-right z-10 hidden md:block">
                    <p className="text-xs font-bold text-gray-400 uppercase">AI Status</p>
                    <p className="text-sm font-mono text-spidy-primary animate-pulse">LIVE SCANNING</p>
                </div>
            </div>

            {/* Pattern Alerts List */}
            <div className="flex-1 overflow-hidden flex flex-col">
                <h4 className="text-xs font-bold text-gray-500 uppercase mb-3 flex items-center gap-2">
                    <AlertOctagon size={14} /> Real-Time Detections
                </h4>
                <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar flex flex-col relative w-full">
                    {!hasData ? (
                        <div className="h-full flex flex-col">
                            {/* Active Scanning Matrix (Visual Only) */}
                            <div className="flex flex-col items-center justify-center opacity-30 mt-10">
                                <Activity size={32} className="animate-pulse text-spidy-primary" />
                                <p className="text-xs font-mono text-spidy-primary mt-2">AWAITING MARKET DATA STREAM...</p>
                            </div>

                            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-70">
                                <div className="relative mb-4">
                                    <div className="absolute inset-0 bg-spidy-primary/20 blur-xl rounded-full animate-pulse" />
                                    <Activity size={48} className="text-spidy-primary relative z-10" />
                                </div>
                                <h5 className="text-sm font-bold text-white mb-1">
                                    Waiting for Data...
                                </h5>
                                <p className="text-xs text-gray-400 max-w-[200px]">Scanning market patterns...</p>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                            {Object.values(analysisData).map((item) => (
                                <motion.div
                                    key={item.symbol}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="bg-white/5 border border-white/10 hover:border-spidy-primary/50 p-3 rounded-xl transition-colors cursor-pointer group flex items-center justify-between"
                                >
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-bold text-sm text-white">{item.symbol}</span>
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${item.trend === 'BULLISH' ? 'bg-green-500/20 text-green-400' :
                                                item.trend === 'BEARISH' ? 'bg-red-500/20 text-red-400' :
                                                    'bg-gray-500/20 text-gray-400'
                                                }`}>
                                                {item.trend}
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-400 mt-1 font-mono">
                                            RSI: <span className={item.rsi > 70 ? 'text-red-400' : item.rsi < 30 ? 'text-green-400' : 'text-gray-300'}>{item.rsi}</span>
                                        </div>
                                    </div>

                                    <div className="text-right">
                                        <div className="text-sm font-mono font-bold text-gray-200">{(item.last_price || 0).toFixed(5)}</div>
                                        <div className="text-[10px] text-gray-500">{item.timestamp}</div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const RiskHQModule = ({ mt5Status }) => (
    <div className="p-6 text-center text-gray-400">
        <Shield size={48} className="mx-auto mb-4 text-red-500 opacity-50" />
        <h3 className="text-xl font-bold text-gray-200">Risk HQ</h3>
        <p className="text-sm">Position Sizing & Kill Switch inactive.</p>
    </div>
);

const TradeDNAModule = () => (
    <div className="p-6 text-center text-gray-400">
        <BookOpen size={48} className="mx-auto mb-4 text-blue-400 opacity-50" />
        <h3 className="text-xl font-bold text-gray-200">Trade DNA</h3>
        <p className="text-sm">Journaling and Psychological analysis.</p>
    </div>
);

const StrategySandboxModule = () => (
    <div className="p-6 text-center text-gray-400">
        <Layers size={48} className="mx-auto mb-4 text-purple-500 opacity-50" />
        <h3 className="text-xl font-bold text-gray-200">Strategy Sandbox</h3>
        <p className="text-sm">Backtesting environment ready.</p>
    </div>
);

export default function FinancialAssistant({ mt5Status }) {
    const [activeModule, setActiveModule] = useState('spider-sense');

    // Indian Context Formatting
    const formatINR = (value) => new Intl.NumberFormat('en-IN', {
        style: 'currency', currency: 'INR', maximumFractionDigits: 0
    }).format(value);

    const tradingBalanceINR = parseFloat(mt5Status?.balance || 0) * 85;

    const modules = [
        { id: 'spider-sense', label: 'Spider-Sense', icon: Zap, color: 'text-spidy-primary' },
        { id: 'risk-hq', label: 'Risk HQ', icon: Shield, color: 'text-red-500' },
        { id: 'trade-dna', label: 'Trade DNA', icon: Activity, color: 'text-blue-400' },
        { id: 'sandbox', label: 'Sandbox', icon: Layers, color: 'text-purple-500' },
    ];

    return (
        <div className="h-full flex flex-col gap-6 pr-2 overflow-hidden">
            {/* Top Bar: Quick Stats (Always Visible) */}
            <div className="flex gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-spidy-primary/10 rounded-lg">
                        <Wallet size={20} className="text-spidy-primary" />
                    </div>
                    <div>
                        <p className="text-xs text-gray-400 font-bold uppercase">Trading Balance</p>
                        <p className="text-xl font-black font-mono text-white">{formatINR(tradingBalanceINR)}</p>
                    </div>
                </div>
                <div className="text-right hidden md:block">
                    <p className="text-xs text-gray-500 italic">Spidy Operations Center v2.0</p>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">

                {/* Sidebar Navigation */}
                <div className="w-full lg:w-64 flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-visible flex-shrink-0">
                    {modules.map((mod) => (
                        <button
                            key={mod.id}
                            onClick={() => setActiveModule(mod.id)}
                            className={`flex items-center gap-3 p-4 rounded-xl border transition-all duration-200 min-w-[150px] lg:min-w-0 ${activeModule === mod.id
                                ? 'bg-white/10 border-spidy-primary/50 text-white shadow-[0_0_15px_rgba(0,255,255,0.1)]'
                                : 'bg-white/5 border-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-200'
                                }`}
                        >
                            <mod.icon size={20} className={activeModule === mod.id ? mod.color : 'text-gray-500'} />
                            <span className="font-bold text-sm tracking-wide">{mod.label}</span>
                        </button>
                    ))}
                </div>

                {/* Module Viewport */}
                <div className="flex-1 bg-black/20 border border-white/10 rounded-2xl relative overflow-hidden flex flex-col">
                    <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-spidy-primary/20 to-transparent" />

                    <div className="flex-1 overflow-y-auto custom-scrollbar">
                        <AnimatePresence mode='wait'>
                            <motion.div
                                key={activeModule}
                                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -10, scale: 0.98 }}
                                transition={{ duration: 0.2 }}
                                className="h-full"
                            >
                                {activeModule === 'spider-sense' && <SpiderSenseModule mt5Status={mt5Status} />}
                                {activeModule === 'risk-hq' && <RiskHQModule mt5Status={mt5Status} />}
                                {activeModule === 'trade-dna' && <TradeDNAModule />}
                                {activeModule === 'sandbox' && <StrategySandboxModule />}
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}
