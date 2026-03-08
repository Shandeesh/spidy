import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Cloud, Power, RefreshCw, Server, Terminal, Download, UploadCloud } from 'lucide-react';
import { motion } from 'framer-motion';

export default function CloudManager() {
    const [status, setStatus] = useState("RUNNING");
    const [uptime, setUptime] = useState("14d 2h 15m");
    const [cpuUsage, setCpuUsage] = useState(12);
    const [memoryUsage, setMemoryUsage] = useState(45);
    const [loading, setLoading] = useState(false);

    // Mock refreshing logs
    // Real Cloud Actions
    const handleAction = async (action) => {
        setLoading(true);
        try {
            console.log(`[Cloud Manager] Action: ${action}`);
            await axios.post('http://localhost:8001/cloud/control', { action });
            if (action === "STOP") setStatus("STOPPED");
            if (action === "START") setStatus("RUNNING");
            if (action === "RESTART") setStatus("RUNNING");
        } catch (e) {
            console.error("Cloud Action Failed", e);
        }
        setLoading(false);
    };

    // Poll Stats
    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await axios.get('http://localhost:8001/cloud/stats');
                if (res.data) {
                    setUptime(res.data.uptime);
                    setCpuUsage(res.data.cpu);
                    setMemoryUsage(res.data.ram);
                    setStatus(res.data.status);
                }
            } catch (e) {
                // If offline, assume stopped or disconnected
                setStatus("OFFLINE");
            }
        };
        fetchStats();
        const interval = setInterval(fetchStats, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-5 flex flex-col gap-4 shadow-xl mb-4"
        >
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-2">
                    <Cloud size={16} className="text-blue-400" />
                    <h3 className="text-sm font-bold text-gray-200 tracking-wide uppercase">Cloud Service Manager</h3>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${status === 'RUNNING' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className={`text-[10px] font-bold uppercase ${status === 'RUNNING' ? 'text-green-400' : 'text-red-400'}`}>
                        {status}
                    </span>
                </div>
            </div>

            {/* Server Stats */}
            <div className="grid grid-cols-3 gap-2">
                <div className="bg-black/20 rounded-lg p-2 flex flex-col items-center">
                    <span className="text-[10px] text-gray-500 uppercase">Uptime</span>
                    <span className="text-xs font-mono font-bold text-gray-300">{uptime}</span>
                </div>
                <div className="bg-black/20 rounded-lg p-2 flex flex-col items-center">
                    <span className="text-[10px] text-gray-500 uppercase">CPU</span>
                    <span className="text-xs font-mono font-bold text-blue-300">{cpuUsage}%</span>
                </div>
                <div className="bg-black/20 rounded-lg p-2 flex flex-col items-center">
                    <span className="text-[10px] text-gray-500 uppercase">RAM</span>
                    <span className="text-xs font-mono font-bold text-purple-300">{memoryUsage}%</span>
                </div>
            </div>

            {/* Controls */}
            <div className="grid grid-cols-3 gap-2 mt-2">
                <button
                    onClick={() => handleAction('START')}
                    disabled={status === 'RUNNING' || loading}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${status === 'RUNNING' ? 'opacity-50 cursor-not-allowed bg-white/5 border-white/5 text-gray-500' : 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20'}`}
                >
                    <Power size={18} />
                    <span className="text-[10px] font-bold mt-1">START</span>
                </button>

                <button
                    onClick={() => handleAction('STOP')}
                    disabled={status === 'STOPPED' || loading}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${status === 'STOPPED' ? 'opacity-50 cursor-not-allowed bg-white/5 border-white/5 text-gray-500' : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'}`}
                >
                    <Power size={18} />
                    <span className="text-[10px] font-bold mt-1">STOP</span>
                </button>

                <button
                    onClick={() => handleAction('RESTART')}
                    disabled={loading}
                    className="flex flex-col items-center justify-center p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 transition-all"
                >
                    <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                    <span className="text-[10px] font-bold mt-1">REBOOT</span>
                </button>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2 mt-2 border-t border-white/10 pt-3">
                <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="flex items-center gap-2"><Server size={12} /> AWS Instance: i-0f32a...</span>
                    <span className="text-[10px] bg-green-900/40 text-green-400 px-1.5 py-0.5 rounded">ap-south-1</span>
                </div>
                <div className="flex gap-2">
                    <button className="flex-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 text-xs text-gray-300 flex items-center justify-center gap-2">
                        <Download size={12} /> Sync Logs
                    </button>
                    <button className="flex-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 text-xs text-gray-300 flex items-center justify-center gap-2">
                        <UploadCloud size={12} /> Deploy Update
                    </button>
                </div>
            </div>
        </motion.div>
    );
}
