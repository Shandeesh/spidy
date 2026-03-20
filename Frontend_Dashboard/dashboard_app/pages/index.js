import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import axios from 'axios';
import { io } from "socket.io-client";
import Sidebar from '../components/Sidebar';
import AIChat from '../components/AIChat';
import TradingDashboard from '../components/TradingDashboard';
import FinancialAssistant from '../components/FinancialAssistant';
import Shoonga from '../components/Shoonga';

const animeVariants = {
    initial: { opacity: 0, x: 100, scale: 0.9, filter: "blur(10px)" }, // More dramatic start
    enter: { opacity: 1, x: 0, scale: 1, filter: "blur(0px)" },
    exit: { opacity: 0, x: -100, scale: 0.9, filter: "blur(10px)" }
};

const animeTransition = {
    type: "spring",
    stiffness: 250,
    damping: 25,
    mass: 0.5
};

export default function Home() {
    const [activeTab, setActiveTab] = useState('trading');
    const [query, setQuery] = useState('');

    // Chat Session Management
    const [sessions, setSessions] = useState([{ id: 1, title: 'New Chat', messages: [], timestamp: Date.now(), theme: 'theme-cyberpunk', persona: 'cyberpunk' }]);
    const [activeSessionId, setActiveSessionId] = useState(1);
    const [isLoaded, setIsLoaded] = useState(false); // Flag to prevent overwriting before load

    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);
    const [mt5Status, setMt5Status] = useState({ connected: false, label: "Offline" });
    const [aiServerStatus, setAiServerStatus] = useState(false); // Real Heartbeat
    const [aiStatus, setAiStatus] = useState("");
    const logsEndRef = useRef(null);

    // Load Sessions from LocalStorage
    useEffect(() => {
        const savedSessions = localStorage.getItem('spidy_sessions');
        if (savedSessions) {
            try {
                const parsed = JSON.parse(savedSessions);
                // Ensure legacy sessions have a theme and persona
                const migrated = parsed.map(s => ({
                    ...s,
                    theme: s.theme || 'theme-cyberpunk',
                    persona: s.persona || 'cyberpunk'
                }));
                // Only set if we actually found something valid
                if (migrated.length > 0) {
                    setSessions(migrated);
                    setActiveSessionId(migrated[0]?.id || 1);
                }
            } catch (e) {
                console.error("Failed to load sessions", e);
            }
        }
        setIsLoaded(true); // Mark as loaded even if empty (to start allowing saves)
    }, []);

    // Save Sessions to LocalStorage
    useEffect(() => {
        if (isLoaded) {
            localStorage.setItem('spidy_sessions', JSON.stringify(sessions));
        }
    }, [sessions, isLoaded]);

    // Helpers
    const createNewSession = () => {
        const newId = Date.now();
        const newSession = { id: newId, title: 'New Chat', messages: [], timestamp: Date.now(), theme: 'theme-cyberpunk', persona: 'cyberpunk' };
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newId);
        setQuery('');
    };

    const updateActiveSession = (newMessages, newTheme = null, newPersona = null) => {
        setSessions(prev => prev.map(session =>
            session.id === activeSessionId
                ? {
                    ...session,
                    messages: newMessages !== null ? newMessages : session.messages,
                    ...(newTheme ? { theme: newTheme } : {}),
                    ...(newPersona ? { persona: newPersona } : {})
                }
                : session
        ));
    };

    const updateSessionTitle = (sessionId, title) => {
        setSessions(prev => prev.map(session =>
            session.id === sessionId ? { ...session, title } : session
        ));
    };

    const deleteSession = (sessionId) => {
        setSessions(prev => {
            const filtered = prev.filter(s => s.id !== sessionId);
            if (filtered.length === 0) {
                // Ensure at least one session exists
                const fallback = { id: Date.now(), title: 'New Chat', messages: [], timestamp: Date.now(), theme: 'theme-cyberpunk', persona: 'cyberpunk' };
                // FIX 17: Switch active session to the fallback
                setActiveSessionId(fallback.id);
                return [fallback];
            }
            // FIX 17: If we deleted the active session, switch to the first remaining
            if (sessionId === activeSessionId) {
                setActiveSessionId(filtered[0].id);
            }
            return filtered;
        });
    };

    // Auto-scroll logs
    const scrollToBottom = () => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // AI Status Socket
    useEffect(() => {
        const socket = io("http://localhost:5000");

        socket.on("connect", () => {
            console.log("Connected to AI Backend Socket");
        });

        socket.on("ai_log", (msg) => {
            // Only show relevant status messages, filter out internal noise if needed
            if (msg.includes("[INFO]") || msg.includes("[WARN]")) {
                setAiStatus(msg.replace("[INFO]", "").replace("[WARN]", "").trim());
            }
        });

        return () => socket.disconnect();
    }, []);

    // OPTIMIZED: Buffered Logs with Auto-Reconnect
    const logBufferRef = useRef([]);
    useEffect(() => {
        let ws = null;
        let reconnectTimer = null;

        const connectWs = () => {
            const wsUrl = 'ws://localhost:8000/ws/logs';
            console.log(`Attempting to connect to System Logs at ${wsUrl}...`);
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("System Logs Connected Successfully");
            };

            ws.onmessage = (event) => {
                logBufferRef.current.push(event.data);
            };

            ws.onclose = (e) => {
                console.warn(`System Logs Disconnected (Code: ${e.code}). Reconnecting in 2s...`);
                reconnectTimer = setTimeout(connectWs, 2000);
            };

            ws.onerror = (err) => {
                console.error("System Logs WebSocket Error:", err);
                ws.close();
            };
        };

        connectWs();

        // Flush logs every 1000ms instead of every message
        const flushInterval = setInterval(() => {
            if (logBufferRef.current.length > 0) {
                setLogs(prev => {
                    const newLogs = [...prev, ...logBufferRef.current];
                    logBufferRef.current = []; // Clear buffer
                    return newLogs.slice(-50); // Keep last 50
                });
            }
        }, 1000);

        return () => {
            if (ws) ws.close();
            if (reconnectTimer) clearTimeout(reconnectTimer);
            clearInterval(flushInterval);
        };
    }, []);

    // Poll MT5 Status
    useEffect(() => {
        const checkStatus = async () => {
            // Check MT5
            try {
                const res = await axios.get('http://localhost:8000/status');
                if (res.data.connected) {
                    setMt5Status({
                        connected: true,
                        label: "Online",
                        ...res.data
                    });
                } else {
                    setMt5Status({ connected: false, label: "Disconnected" });
                }
            } catch (e) {
                setMt5Status({ connected: false, label: "Offline" });
            }

            // Check AI Brain Heartbeat
            try {
                const resAI = await axios.get('http://localhost:5001/status', { timeout: 1000 });
                if (resAI.data.status === "online") {
                    setAiServerStatus(true);
                } else {
                    setAiServerStatus(false);
                }
            } catch (e) {
                setAiServerStatus(false);
            }
        };

        // Auto-Connect on Mount (One-Click Launch) with Retry
        const initConnection = async () => {
            let attempts = 0;
            const maxAttempts = 5; // Reduced attempts to avoid spamming if down

            const attemptConnect = async () => {
                try {
                    await axios.post('http://localhost:8000/connect');
                    console.log("Auto-connect Triggered");
                } catch (e) {
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(attemptConnect, 3000);
                    }
                }
            };

            attemptConnect();
        };

        initConnection();
        // Initial Check
        checkStatus();
        // Reverted to 1s for smooth clock updates
        const interval = setInterval(checkStatus, 1000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [logs]);

    const handleAsk = async (manualQuery = null, imageFile = null, newPersonaSelection = null, modelMode = "turbo") => {
        // If it's just a persona switch (no query, no image)
        if (newPersonaSelection) {
            updateActiveSession(null, null, newPersonaSelection);
            return;
        }

        // Check if manualQuery is a string (direct call) vs event object (button click)
        const isManual = typeof manualQuery === 'string';
        const queryToUse = isManual ? manualQuery : query;

        if (!queryToUse.trim() && !imageFile) return;

        if (!isManual) {
            setQuery(''); // Only clear input if it was typed
        }

        setLoading(true);

        // Add User Message
        const userMsgContent = imageFile
            ? `[Image Attached] ${queryToUse}`
            : queryToUse;

        const userMsg = { role: 'user', content: userMsgContent };

        // Optimistic Update
        let currentMessages = sessions.find(s => s.id === activeSessionId)?.messages || [];
        const activePersona = sessions.find(s => s.id === activeSessionId)?.persona || 'cyberpunk';

        const updatedWithUser = [...currentMessages, userMsg];
        updateActiveSession(updatedWithUser);

        // Auto-Title: If this is the first message (or close to it), update title
        if (currentMessages.length === 0) {
            // Simple logic: Use first 30 chars of query
            const newTitle = queryToUse.substring(0, 30) + (queryToUse.length > 30 ? "..." : "");
            updateSessionTitle(activeSessionId, newTitle);
        }

        try {
            // Convert Image to Base64 if present
            let base64Image = null;
            if (imageFile) {
                base64Image = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.readAsDataURL(imageFile);
                });
            }

            // Direct call to fast AI Server
            const payload = {
                query: queryToUse,
                persona: activePersona,
                model_mode: modelMode // UPGRADE 5: pass modelMode
            };
            if (base64Image) {
                payload.image = base64Image;
            }

            const res = await axios.post('http://localhost:5001/api/ask', payload);

            // Add AI Response
            const aiMsg = { role: 'ai', content: res.data };

            // Check for theme/persona suggestion
            let newTheme = null;
            let newPersona = null;

            if (res.data.theme) {
                newTheme = `theme-${res.data.theme}`;
                newPersona = res.data.theme; // Auto-update persona to match theme
            }

            updateActiveSession([...updatedWithUser, aiMsg], newTheme, newPersona);

        } catch (error) {
            console.error("API Error", error);
            const errorMsg = { role: 'ai', content: { error: "Failed to reach Spidy Backend" } };
            updateActiveSession([...updatedWithUser, errorMsg]);
        }
        setLoading(false);
    };

    // Get current theme
    const activeSession = sessions.find(s => s.id === activeSessionId);
    const currentTheme = activeSession?.theme || 'theme-cyberpunk';

    return (
        <div className={`flex h-screen bg-spidy-dark text-white font-sans selection:bg-spidy-primary selection:text-white overflow-hidden relative transition-colors duration-500 ${currentTheme}`}>
            {/* OPTIMIZED: Background Gradient using CSS radial-gradient instead of expensive blur divs 
                We use an absolute div with 2 radial gradients to mimic the mesh effect more cheaply.
            */}
            <div
                className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 opacity-20 pointer-events-none"
                style={{
                    backgroundImage: `
                        radial-gradient(circle at 10% 10%, var(--color-primary) 0%, transparent 40%),
                        radial-gradient(circle at 90% 90%, var(--color-accent) 0%, transparent 40%)
                    `
                }}
            />

            {/* Sidebar Navigation */}
            <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} mt5Status={mt5Status} />

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="flex items-center justify-between p-4 bg-white/5 backdrop-blur-lg border-b border-white/10 z-20">
                    <h2 className="text-xl font-bold text-gray-200">
                        {activeTab === 'ai' ? 'AI Command Center' :
                            activeTab === 'trading' ? 'Live Trading Floor' :
                                activeTab === 'shoonga' ? 'Shoonga Floor' :
                                    'Financial Assistant'}
                    </h2>
                    <div className="flex gap-4 items-center">
                        {mt5Status.connected && (
                            <div className="hidden md:flex items-center gap-4 bg-black/20 px-3 py-1.5 rounded-lg border border-white/5">
                                <div className="flex flex-col items-end leading-none">
                                    <span className="text-[10px] text-gray-500 uppercase">Balance</span>
                                    <span className="text-sm font-bold text-gray-200">${typeof mt5Status.balance === 'number' ? mt5Status.balance.toFixed(2) : (mt5Status.balance || '0.00')}</span>
                                </div>
                                <div className="h-6 w-px bg-white/10" />
                                <div className="flex flex-col items-start leading-none">
                                    <span className="text-[10px] text-gray-500 uppercase">Profit</span>
                                    <span className={`text-sm font-bold ${parseFloat(mt5Status.profit) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        ${typeof mt5Status.profit === 'number' ? mt5Status.profit.toFixed(2) : (mt5Status.profit || '0.00')}
                                    </span>
                                </div>
                            </div>
                        )}
                        <ReconnectButton />
                        <StatusIndicator label="MT5 Bridge" status={mt5Status.label} active={mt5Status.connected} />
                        <StatusIndicator label="AI Brain" status={aiServerStatus ? "Online" : "Offline"} active={aiServerStatus} />
                    </div>
                </header>

                <main className="flex-1 overflow-hidden p-6 relative">
                    <AnimatePresence mode="wait">
                        {activeTab === 'ai' ? (
                            <motion.div
                                key="ai"
                                variants={animeVariants}
                                initial="initial"
                                animate="enter"
                                exit="exit"
                                transition={animeTransition}
                                className="h-full w-full"
                            >
                                <AIChat
                                    sessions={sessions}
                                    activeSessionId={activeSessionId}
                                    onSelectSession={setActiveSessionId}
                                    onNewSession={createNewSession}
                                    onDeleteSession={deleteSession} // Optional
                                    loading={loading}
                                    query={query}
                                    setQuery={setQuery}
                                    handleAsk={handleAsk}
                                    aiStatus={aiStatus}
                                />
                            </motion.div>
                        ) : activeTab === 'trading' ? (
                            <motion.div
                                key="trading"
                                variants={animeVariants}
                                initial="initial"
                                animate="enter"
                                exit="exit"
                                transition={animeTransition}
                                className="h-full w-full"
                            >
                                <TradingDashboard
                                    mt5Status={mt5Status}
                                    logs={logs}
                                    logsEndRef={logsEndRef}
                                />
                            </motion.div>
                        ) : activeTab === 'shoonga' ? (
                            <motion.div
                                key="shoonga"
                                variants={animeVariants}
                                initial="initial"
                                animate="enter"
                                exit="exit"
                                transition={animeTransition}
                                className="h-full w-full"
                            >
                                <Shoonga />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="financial"
                                variants={animeVariants}
                                initial="initial"
                                animate="enter"
                                exit="exit"
                                transition={animeTransition}
                                className="h-full w-full"
                            >
                                <FinancialAssistant mt5Status={mt5Status} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>
            </div>
        </div>
    );
}

function ReconnectButton() {
    const [loading, setLoading] = useState(false);

    const handleReconnect = async () => {
        setLoading(true);
        try {
            await axios.post('http://localhost:8000/connect');
        } catch (e) {
            console.error(e);
        }
        // Keep loading true for a bit longer to simulate wait/cooldown or wait for next poll
        setTimeout(() => setLoading(false), 5000);
    };

    return (
        <button
            onClick={handleReconnect}
            disabled={loading}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all border border-white/5 flex items-center gap-2 ${loading ? 'bg-yellow-500/20 text-yellow-400 cursor-wait' : 'bg-white/10 hover:bg-white/20 text-white'}`}
        >
            {loading ? (
                <>
                    <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    Connecting...
                </>
            ) : (
                "Reconnect MT5"
            )}
        </button>
    );
}

function StatusIndicator({ label, status, active }) {
    return (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/20 border border-white/5 text-xs font-medium">
            <div className={`w-2 h-2 rounded-full ${active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className={active ? 'text-gray-200' : 'text-gray-500'}>{label}</span>
        </div>
    );
}
