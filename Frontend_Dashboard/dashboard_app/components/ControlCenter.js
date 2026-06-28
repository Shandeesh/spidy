import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
    Terminal, Sliders, Database, Play, AlertCircle, 
    CheckCircle2, XCircle, Shield, RefreshCw, Send 
} from 'lucide-react';

export default function ControlCenter() {
    const [dbState, setDbState] = useState(null);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState({});
    const [consoleLogs, setConsoleLogs] = useState("Antigravity 2.0 system initialized. Standing by...\nSelect 'Run Update' on any floor to trigger telemetry audit.");
    const [feedbackInput, setFeedbackInput] = useState({
        floor: 'spidy',
        message: '',
        level: 'info'
    });

    // Fetch loop status
    const fetchStatus = async () => {
        try {
            const res = await axios.get('http://localhost:5001/api/update-center/status');
            setDbState(res.data);
        } catch (e) {
            console.error("Failed to fetch update center status", e);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const updateConfig = async (floor, field, value) => {
        if (!dbState) return;
        const currentConfig = dbState.config[floor] || {
            auto_update: true,
            plan_mode: true,
            strict_testing: true,
            max_retries: 3
        };
        const updated = { ...currentConfig, [field]: value };
        try {
            await axios.post('http://localhost:5001/api/update-center/config', {
                floor,
                ...updated
            });
            fetchStatus();
        } catch (e) {
            console.error("Failed to update config", e);
        }
    };

    const handleFeedbackSubmit = async (e) => {
        e.preventDefault();
        if (!feedbackInput.message.trim()) return;
        setLoading(true);
        try {
            await axios.post('http://localhost:5001/api/update-center/feedback', {
                floor: feedbackInput.floor,
                message: feedbackInput.message,
                level: feedbackInput.level,
                source: 'user'
            });
            setFeedbackInput(prev => ({ ...prev, message: '' }));
            fetchStatus();
        } catch (e) {
            console.error("Failed to submit feedback", e);
        }
        setLoading(false);
    };

    const triggerAudit = async (floor) => {
        setActionLoading(prev => ({ ...prev, [floor]: true }));
        setConsoleLogs(`[SYSTEM] Triggering Antigravity 2.0 Telemetry Loop for floor: ${floor.toUpperCase()}...\n`);
        try {
            const res = await axios.post('http://localhost:5001/api/update-center/trigger', { floor });
            setConsoleLogs(prev => prev + (res.data.logs || "Audit completed. No changes applied."));
            fetchStatus();
        } catch (e) {
            setConsoleLogs(prev => prev + `\n[ERROR] Audit request failed: ${e.message}`);
        }
        setActionLoading(prev => ({ ...prev, [floor]: false }));
    };

    const approvePlan = async (floor) => {
        setActionLoading(prev => ({ ...prev, [`approve_${floor}`]: true }));
        setConsoleLogs(`[SYSTEM] Approving and deploying plan for ${floor.toUpperCase()}...\n`);
        try {
            const res = await axios.post('http://localhost:5001/api/update-center/approve', { floor });
            setConsoleLogs(prev => prev + "\n" + (res.data.logs || "Deployment complete."));
            fetchStatus();
        } catch (e) {
            setConsoleLogs(prev => prev + `\n[ERROR] Deployment failed: ${e.message}`);
        }
        setActionLoading(prev => ({ ...prev, [`approve_${floor}`]: false }));
    };

    const rejectPlan = async (floor) => {
        setActionLoading(prev => ({ ...prev, [`reject_${floor}`]: true }));
        setConsoleLogs(`[SYSTEM] Rejecting plan for ${floor.toUpperCase()}...\n`);
        try {
            const res = await axios.post('http://localhost:5001/api/update-center/reject', { floor });
            setConsoleLogs(prev => prev + "\n" + (res.data.logs || "Plan rejected and cleared."));
            fetchStatus();
        } catch (e) {
            setConsoleLogs(prev => prev + `\n[ERROR] Rejection failed: ${e.message}`);
        }
        setActionLoading(prev => ({ ...prev, [`reject_${floor}`]: false }));
    };

    if (!dbState) {
        return (
            <div className="flex h-full items-center justify-center text-gray-400">
                <RefreshCw className="animate-spin mr-2" />
                Loading Update Center State...
            </div>
        );
    }

    const floors = ['spidy', 'trade_ai', 'shooya'];
    const pendingPlans = dbState.pending_plans || {};

    const getStatusBadge = (floor) => {
        const hasPlan = pendingPlans[floor];
        const lastUpdate = dbState.update_history.filter(u => u.floor === floor).slice(-1)[0];
        const pendingItems = dbState.feedback_loop.filter(f => f.floor === floor && f.status === 'pending');
        const blockedItems = dbState.feedback_loop.filter(f => f.floor === floor && f.status === 'blocked');

        if (blockedItems.length > 0) {
            return <span className="px-2 py-0.5 text-xs font-semibold bg-red-500/20 text-red-400 rounded border border-red-500/30">BLOCKED</span>;
        }
        if (hasPlan) {
            return <span className="px-2 py-0.5 text-xs font-semibold bg-yellow-500/20 text-yellow-400 rounded border border-yellow-500/30">PENDING REVIEW</span>;
        }
        if (pendingItems.length > 0) {
            return <span className="px-2 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-400 rounded border border-blue-500/30">AUDITING TELEMETRY</span>;
        }
        return <span className="px-2 py-0.5 text-xs font-semibold bg-green-500/20 text-green-400 rounded border border-green-500/30">ACTIVE</span>;
    };

    const getFloorVersion = (floor) => {
        const lastSuccess = dbState.update_history
            .filter(u => u.floor === floor && u.status === 'success')
            .slice(-1)[0];
        return lastSuccess ? lastSuccess.version_after : (floor === 'spidy' ? 'v1.4.2' : floor === 'trade_ai' ? 'v3.1.0' : 'v2.0.4');
    };

    return (
        <div className="h-full overflow-y-auto pr-2 space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10 shadow-xl">
                <div>
                    <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-spidy-primary to-orange-500 flex items-center gap-2">
                        <Terminal className="text-spidy-primary animate-pulse" />
                        Multi-Floor Update Center
                    </h1>
                    <p className="text-sm text-gray-400 mt-1">Antigravity 2.0 Autonomous Self-Updating Pipeline Manager</p>
                </div>
                <button 
                    onClick={fetchStatus} 
                    className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-lg border border-white/5 transition-all flex items-center gap-2 text-sm font-medium"
                >
                    <RefreshCw size={16} />
                    Sync Loop
                </button>
            </div>

            {/* Floor Cards Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {floors.map(floor => {
                    const cfg = dbState.config[floor] || {
                        auto_update: true,
                        plan_mode: true,
                        strict_testing: true,
                        max_retries: 3
                    };
                    const isSpidy = floor === 'spidy';
                    const label = isSpidy ? "Spidy AI Core" : floor === 'trade_ai' ? "Trade AI Platform" : "Shooya (Shoonya Bridge)";

                    return (
                        <div key={floor} className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col justify-between hover:border-white/20 transition-all shadow-lg relative overflow-hidden group">
                            {/* Accent Glow */}
                            <div className="absolute -right-16 -top-16 w-32 h-32 bg-spidy-primary/5 rounded-full blur-2xl group-hover:bg-spidy-primary/10 transition-all pointer-events-none" />
                            
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-200">{label}</h3>
                                        <div className="flex items-center gap-2 mt-1.5">
                                            <span className="text-[11px] font-mono px-2 py-0.5 bg-white/5 text-gray-400 rounded-full border border-white/5">{getFloorVersion(floor)}</span>
                                            {getStatusBadge(floor)}
                                        </div>
                                    </div>
                                    <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-lg shadow-inner">
                                        {isSpidy ? "🕷️" : floor === 'trade_ai' ? "📈" : "⚡"}
                                    </div>
                                </div>

                                <div className="h-px bg-white/10 my-4" />

                                {/* Pipeline Settings / Guardrails */}
                                <div className="space-y-3.5">
                                    <h4 className="text-[11px] font-extrabold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                                        <Sliders size={12} className="text-spidy-primary" /> Guardrails & Config
                                    </h4>

                                    <label className="flex items-center justify-between text-xs text-gray-300 cursor-pointer hover:text-white transition-colors">
                                        <span>Auto-Update Loop (2 AM)</span>
                                        <input 
                                            type="checkbox" 
                                            checked={cfg.auto_update} 
                                            onChange={(e) => updateConfig(floor, 'auto_update', e.target.checked)}
                                            className="w-4 h-4 accent-spidy-primary bg-black/40 rounded border-white/10 focus:ring-0 cursor-pointer"
                                        />
                                    </label>

                                    <label className="flex items-center justify-between text-xs text-gray-300 cursor-pointer hover:text-white transition-colors">
                                        <span>Require Review Plan (Plan Mode)</span>
                                        <input 
                                            type="checkbox" 
                                            checked={cfg.plan_mode} 
                                            onChange={(e) => updateConfig(floor, 'plan_mode', e.target.checked)}
                                            className="w-4 h-4 accent-spidy-primary bg-black/40 rounded border-white/10 focus:ring-0 cursor-pointer"
                                        />
                                    </label>

                                    <label className="flex items-center justify-between text-xs text-gray-300 cursor-pointer hover:text-white transition-colors">
                                        <span>Strict Integration Testing</span>
                                        <input 
                                            type="checkbox" 
                                            checked={cfg.strict_testing} 
                                            onChange={(e) => updateConfig(floor, 'strict_testing', e.target.checked)}
                                            className="w-4 h-4 accent-spidy-primary bg-black/40 rounded border-white/10 focus:ring-0 cursor-pointer"
                                        />
                                    </label>

                                    <div className="flex items-center justify-between text-xs text-gray-300">
                                        <span>Max Retries (Loop Prevention)</span>
                                        <input 
                                            type="number" 
                                            min="1"
                                            max="10"
                                            value={cfg.max_retries} 
                                            onChange={(e) => updateConfig(floor, 'max_retries', parseInt(e.target.value) || 3)}
                                            className="w-12 h-6 px-1 text-center bg-black/40 border border-white/10 text-white rounded focus:outline-none focus:border-spidy-primary transition-all text-xs font-mono"
                                        />
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={() => triggerAudit(floor)}
                                disabled={actionLoading[floor]}
                                className="w-full mt-6 py-2.5 bg-spidy-primary hover:bg-spidy-primary/80 disabled:bg-gray-800 disabled:text-gray-500 text-white text-xs font-bold rounded-xl transition-all shadow-md shadow-spidy-primary/10 flex items-center justify-center gap-2 group-hover:scale-[1.02]"
                            >
                                {actionLoading[floor] ? (
                                    <>
                                        <RefreshCw size={14} className="animate-spin" />
                                        Running Pipeline...
                                    </>
                                ) : (
                                    <>
                                        <Play size={14} fill="currentColor" />
                                        Run Update Audit
                                    </>
                                )}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Pending Approval Plan Section */}
            {floors.some(f => pendingPlans[f]) && (
                <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-2xl p-6 shadow-lg space-y-4">
                    <h2 className="text-base font-extrabold text-yellow-400 flex items-center gap-2">
                        <AlertCircle className="text-yellow-400 animate-pulse" /> 
                        Review-Driven Development: Pending Plans Waiting Approval
                    </h2>
                    
                    {floors.map(floor => {
                        const plan = pendingPlans[floor];
                        if (!plan) return null;
                        
                        return (
                            <div key={floor} className="bg-black/40 border border-white/5 rounded-xl p-5 space-y-4">
                                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 bg-yellow-400/20 text-yellow-400 rounded border border-yellow-400/30">{floor.toUpperCase()} PLAN</span>
                                            <span className="text-xs text-gray-500 font-mono">{plan.timestamp}</span>
                                        </div>
                                        <h3 className="text-base font-bold text-gray-100 mt-1">{plan.title}</h3>
                                        <p className="text-xs text-gray-400 mt-0.5">{plan.description}</p>
                                    </div>
                                    
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => rejectPlan(floor)}
                                            disabled={actionLoading[`reject_${floor}`]}
                                            className="px-4 py-2 bg-red-500/20 hover:bg-red-500 text-red-400 hover:text-white disabled:bg-gray-800 disabled:text-gray-500 rounded-lg text-xs font-semibold border border-red-500/30 transition-all"
                                        >
                                            {actionLoading[`reject_${floor}`] ? "Rejecting..." : "Reject"}
                                        </button>
                                        <button
                                            onClick={() => approvePlan(floor)}
                                            disabled={actionLoading[`approve_${floor}`]}
                                            className="px-5 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-green-500/10 transition-all flex items-center gap-2"
                                        >
                                            {actionLoading[`approve_${floor}`] ? (
                                                <>
                                                    <RefreshCw size={12} className="animate-spin" />
                                                    Deploying...
                                                </>
                                            ) : (
                                                <>
                                                    <CheckCircle2 size={12} />
                                                    Approve & Deploy
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>

                                {/* Proposed Diffs */}
                                <div className="space-y-2.5">
                                    <h4 className="text-xs font-semibold text-gray-400">Proposed File Changes:</h4>
                                    {plan.files.map((file, idx) => (
                                        <div key={idx} className="border border-white/5 rounded-lg overflow-hidden font-mono text-xs">
                                            <div className="bg-white/5 px-4 py-2 border-b border-white/5 flex justify-between text-[11px] text-gray-400">
                                                <span>{file.path}</span>
                                                <span className="text-yellow-400">{file.action}</span>
                                            </div>
                                            <pre className="p-4 bg-black/60 overflow-x-auto text-[11px] leading-relaxed max-h-48 whitespace-pre text-gray-300">
                                                {file.diff.split('\n').map((line, lIdx) => {
                                                    let color = "text-gray-400";
                                                    if (line.startsWith('+')) color = "text-green-400 bg-green-950/20";
                                                    else if (line.startsWith('-')) color = "text-red-400 bg-red-950/20";
                                                    else if (line.startsWith('@@')) color = "text-cyan-400";
                                                    return (
                                                        <div key={lIdx} className={`px-2 py-0.5 ${color}`}>
                                                            {line}
                                                        </div>
                                                    );
                                                })}
                                            </pre>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Bottom Row: Pipeline Log Console + Telemetry Loop Database */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Console Log */}
                <div className="bg-black/60 border border-white/10 rounded-2xl p-5 flex flex-col h-[400px] overflow-hidden shadow-2xl relative">
                    <div className="flex justify-between items-center mb-3">
                        <h3 className="text-sm font-extrabold text-gray-300 flex items-center gap-2">
                            <Terminal size={14} className="text-spidy-primary animate-pulse" />
                            Antigravity 2.0 Pipeline Terminal
                        </h3>
                        <div className="flex gap-1">
                            <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                            <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                        </div>
                    </div>

                    <div className="flex-1 bg-black/80 rounded-xl p-4 overflow-y-auto font-mono text-[11px] text-green-400 border border-white/5 space-y-1 scrollbar-thin select-text">
                        {consoleLogs.split('\n').map((line, idx) => {
                            let color = "text-green-400";
                            if (line.includes("[ERROR]") || line.includes("[CRITICAL]")) color = "text-red-400 font-bold";
                            else if (line.includes("[WARNING]")) color = "text-yellow-400";
                            else if (line.includes("[PLAN]")) color = "text-cyan-400";
                            else if (line.includes("[DEPLOY]")) color = "text-indigo-400 font-bold";
                            else if (line.includes("[AUDIT]")) color = "text-blue-400";
                            
                            return (
                                <div key={idx} className={color}>
                                    {line}
                                </div>
                            );
                        })}
                        <span className="inline-block w-1.5 h-3.5 bg-green-400 ml-1 animate-pulse" />
                    </div>
                </div>

                {/* Telemetry Loop Database & Input */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col h-[400px] shadow-lg">
                    <h3 className="text-sm font-extrabold text-gray-300 flex items-center gap-2 mb-4">
                        <Database size={14} className="text-spidy-primary" />
                        Telemetry Loop & Feedback Database
                    </h3>
                    
                    {/* Add Feedback Form */}
                    <form onSubmit={handleFeedbackSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                        <select 
                            value={feedbackInput.floor}
                            onChange={(e) => setFeedbackInput(prev => ({ ...prev, floor: e.target.value }))}
                            className="bg-black/40 border border-white/10 text-xs text-gray-300 rounded-lg p-2 focus:outline-none focus:border-spidy-primary font-medium"
                        >
                            <option value="spidy">Spidy AI</option>
                            <option value="trade_ai">Trade AI</option>
                            <option value="shooya">Shooya</option>
                        </select>
                        <select 
                            value={feedbackInput.level}
                            onChange={(e) => setFeedbackInput(prev => ({ ...prev, level: e.target.value }))}
                            className="bg-black/40 border border-white/10 text-xs text-gray-300 rounded-lg p-2 focus:outline-none focus:border-spidy-primary font-medium"
                        >
                            <option value="info">Info / Suggestion</option>
                            <option value="warning">Warning / Warning</option>
                            <option value="error">Error / Crash Report</option>
                        </select>
                        <div className="relative flex">
                            <input 
                                type="text"
                                placeholder="Submit crash message or bug..."
                                value={feedbackInput.message}
                                onChange={(e) => setFeedbackInput(prev => ({ ...prev, message: e.target.value }))}
                                className="w-full bg-black/40 border border-white/10 text-xs text-white placeholder-gray-500 rounded-lg pl-3 pr-10 focus:outline-none focus:border-spidy-primary"
                            />
                            <button 
                                type="submit" 
                                disabled={loading}
                                className="absolute right-1 top-1 bottom-1 px-2.5 bg-spidy-primary hover:bg-spidy-primary/80 text-white rounded-md transition-colors flex items-center justify-center"
                            >
                                <Send size={12} />
                            </button>
                        </div>
                    </form>

                    {/* Feedback database list */}
                    <div className="flex-1 overflow-y-auto space-y-2.5 border border-white/5 rounded-xl bg-black/20 p-3">
                        {dbState.feedback_loop.length === 0 ? (
                            <div className="text-center text-xs text-gray-500 py-10">No telemetry log entries found.</div>
                        ) : (
                            [...dbState.feedback_loop].reverse().map(fb => {
                                let borderClass = "border-white/5 bg-white/5";
                                let icon = <CheckCircle2 size={12} className="text-green-500" />;
                                
                                if (fb.status === 'blocked') {
                                    borderClass = "border-red-500/20 bg-red-950/10";
                                    icon = <XCircle size={12} className="text-red-500" />;
                                } else if (fb.status === 'pending' || fb.status === 'patch_created') {
                                    borderClass = "border-yellow-500/20 bg-yellow-950/10";
                                    icon = <AlertCircle size={12} className="text-yellow-500 animate-pulse" />;
                                }

                                return (
                                    <div key={fb.id} className={`p-3 rounded-lg border flex justify-between gap-3 text-xs ${borderClass}`}>
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="font-extrabold uppercase text-[9px] text-gray-400 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">{fb.floor.toUpperCase()}</span>
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold ${fb.level === 'error' ? 'bg-red-500/20 text-red-400' : fb.level === 'warning' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}`}>{fb.level}</span>
                                                <span className="text-[10px] text-gray-500 font-mono">{new Date(fb.timestamp).toLocaleTimeString()}</span>
                                            </div>
                                            <p className="text-gray-300 leading-snug">{fb.message}</p>
                                        </div>
                                        <div className="flex flex-col items-center justify-center flex-shrink-0">
                                            {icon}
                                            <span className="text-[8px] uppercase tracking-wider text-gray-500 mt-1 font-bold">{fb.status}</span>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
