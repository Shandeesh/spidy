import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from 'axios';
import { Send, Activity, Terminal, Cpu, Mic, Image as ImageIcon, Zap, Brain, Sparkles, ChevronDown, Shield, TrendingUp, X, MessageSquare, Plus, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ChatSidebar = ({ sessions, activeSessionId, onSelectSession, onNewSession, onDeleteSession }) => {
    return (
        <div className="w-64 bg-black/20 border-r border-white/5 flex flex-col h-full shrink-0">
            {/* New Chat Button */}
            <div className="p-4">
                <button
                    onClick={onNewSession}
                    className="w-full flex items-center justify-center gap-2 bg-spidy-primary hover:bg-red-600 text-white rounded-xl py-3 text-sm font-bold shadow-lg shadow-spidy-primary/20 transition-all active:scale-95"
                >
                    <Plus size={16} /> New Chat
                </button>
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto px-2 custom-scrollbar">
                <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 px-2">History</div>
                <div className="space-y-1">
                    {sessions.map((session) => (
                        <div
                            key={session.id}
                            className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all border border-transparent ${session.id === activeSessionId
                                ? 'bg-white/10 border-white/10 text-white shadow-sm'
                                : 'hover:bg-white/5 text-gray-400 hover:text-gray-200'
                                }`}
                            onClick={() => onSelectSession(session.id)}
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <MessageSquare size={16} className={session.id === activeSessionId ? 'text-spidy-primary' : 'text-gray-500'} />
                                <span className="truncate text-sm font-medium">{session.title || 'Untitled Chat'}</span>
                            </div>

                            {/* Delete Option (Visible on Hover or Active) */}
                            {onDeleteSession && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteSession(session.id);
                                    }}
                                    className={`p-1.5 rounded-md hover:bg-red-500/20 hover:text-red-400 transition-colors ${session.id === activeSessionId ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                        }`}
                                >
                                    <Trash2 size={12} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            <div className="p-4 mt-auto border-t border-white/5">
                <div className="flex items-center gap-2 text-gray-500 text-xs">
                    <Brain size={14} />
                    <span>Spidy Memory: {sessions.length} Sessions</span>
                </div>
            </div>
        </div>
    );
};

export default function AIChat({ sessions = [], activeSessionId, onSelectSession, onNewSession, onDeleteSession, loading, query, setQuery, handleAsk, aiStatus }) {
    const [modelMode, setModelMode] = useState('turbo'); // 'turbo' | 'deep'
    const [isRecording, setIsRecording] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const fileInputRef = useRef(null);

    // Derived State
    const currentSession = sessions.find(s => s.id === activeSessionId);
    const chatHistory = currentSession?.messages || [];

    const quickPrompts = [
        { label: "Analyze Market", icon: Activity, prompt: "Analyze current market sentiment for EURUSD and XAUUSD." },
        { label: "Risk Report", icon: Shield, prompt: "Generate a risk assessment for my current open positions." },
        { label: "Forecast", icon: TrendingUp, prompt: "What is the technical forecast for the next 4 hours?" },
    ];

    const handleQuickPrompt = (prompt) => {
        handleAsk(prompt);
    };

    const handleImageClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e) => {
        if (e.target.files?.[0]) {
            setSelectedFile(e.target.files[0]);
            // Optional: Set default query if empty
            if (!query) setQuery("Describe this image.");
        }
    };

    const chatEndRef = useRef(null);  // UPGRADE 8: auto-scroll target

    // UPGRADE 8: Auto-scroll to bottom whenever chatHistory changes
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory, loading]);

    const onSend = () => {
        handleAsk(query, selectedFile, null, modelMode);  // UPGRADE 5: pass modelMode
        setQuery('');
        setSelectedFile(null);
    };

    const clearFile = () => {
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const toggleVoice = async () => {
        if (!isRecording) {
            setIsRecording(true);
            setQuery("Listening... (Speak into your microphone)");

            try {
                // Call backend to trigger server-side listening
                const res = await axios.post('http://localhost:5001/api/listen');

                if (res.data.transcript) {
                    setQuery(res.data.transcript);
                    // Optional: Auto-send if transcript is clear
                    // handleAsk(res.data.transcript); 
                } else {
                    setQuery("Could not hear anything.");
                }
            } catch (error) {
                console.error("Voice Error", error);
                setQuery("Voice Module Error: Check Backend Console.");
            } finally {
                setIsRecording(false);
            }
        } else {
            // If user clicks again, we can't really "cancel" the server thread easily 
            // without a cancel endpoint, but we can reset UI
            setIsRecording(false);
            setQuery("");
        }
    };

    return (
        <div className="flex h-full bg-spidy-card/30 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
            {/* LEFT SIDEBAR */}
            <ChatSidebar
                sessions={sessions}
                activeSessionId={activeSessionId}
                onSelectSession={onSelectSession}
                onNewSession={onNewSession}
                onDeleteSession={onDeleteSession}
            />

            {/* RIGHT MAIN CHAT AREA */}
            <div className="flex-1 flex flex-col h-full min-w-0 bg-transparent">

                {/* Header / Mode Switcher (Moved inside main area) */}
                <div className="flex items-center justify-between p-4 border-b border-white/5 bg-black/10">
                    <div className="flex items-center gap-2 text-gray-400">
                        <Terminal size={18} />
                        <span className="text-sm font-mono tracking-wider">
                            {currentSession?.title || 'AI OPERATIONS'}
                        </span>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Auto-Persona Indicator (Read Only) */}
                        <div className="relative group">
                            <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 bg-black/20 px-3 py-1.5 rounded-lg border border-white/5 select-none cursor-help" title="Spidy automatically adapts its persona based on your conversation.">
                                <span className="text-spidy-primary">AUTO-MODE:</span>
                                <span>{currentSession?.persona ? currentSession.persona.toUpperCase() : 'CYBERPUNK'}</span>
                            </div>
                        </div>

                        <div className="h-4 w-px bg-white/10" />

                        {/* Mode Switcher */}
                        <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
                            <button
                                onClick={() => setModelMode('turbo')}
                                className={`px-3 py-1 rounded-md text-xs font-bold flex items-center gap-2 transition-all ${modelMode === 'turbo' ? 'bg-spidy-primary text-white shadow-lg shadow-spidy-primary/20' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                <Zap size={12} /> TURBO
                            </button>
                            <button
                                onClick={() => setModelMode('deep')}
                                className={`px-3 py-1 rounded-md text-xs font-bold flex items-center gap-2 transition-all ${modelMode === 'deep' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                <Brain size={12} /> DEEP
                            </button>
                        </div>
                    </div>
                </div>

                {/* Terminal / Response Area */}
                <div className="flex-1 p-6 overflow-y-auto relative flex flex-col">
                    <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar">
                        <AnimatePresence initial={false} mode="wait">
                            {chatHistory.length === 0 ? (
                                <motion.div
                                    key="empty-state"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="flex-1 flex items-center justify-center text-gray-600 flex-col gap-6 min-h-[200px]"
                                >
                                    <div className="relative">
                                        <div className="absolute inset-0 bg-spidy-primary/10 blur-xl rounded-full animate-pulse" />
                                        <Cpu size={64} className="text-spidy-primary/50 relative z-10" />
                                    </div>
                                    <div className="text-center">
                                        <p className="text-lg font-bold text-gray-300">System Online</p>
                                        <p className="text-sm text-gray-500">Select a quick action or type a command.</p>
                                    </div>

                                    {/* Quick Prompts Grid */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-lg mt-4">
                                        {quickPrompts.map((qp, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleQuickPrompt(qp.prompt)}
                                                className="bg-white/5 hover:bg-white/10 border border-white/5 hover:border-spidy-primary/30 p-3 rounded-xl flex flex-col items-center gap-2 text-gray-400 hover:text-white transition-all group"
                                            >
                                                <qp.icon size={20} className="text-gray-500 group-hover:text-spidy-primary transition-colors" />
                                                <span className="text-xs font-bold">{qp.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            ) : (
                                chatHistory.map((msg, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} group`}
                                    >
                                        {/* UPGRADE 9: Timestamp shown on group-hover */}
                                        <div className="relative max-w-[85%]">
                                            <div className={`p-4 rounded-2xl ${msg.role === 'user'
                                                    ? 'bg-spidy-primary/20 border border-spidy-primary/30 text-white rounded-tr-none shadow-[0_0_15px_rgba(255,50,50,0.1)]'
                                                    : 'bg-white/10 border border-white/5 text-gray-300 rounded-tl-none font-mono text-sm'
                                                }`}>
                                                {msg.role === 'user' ? (
                                                    msg.content
                                                ) : (
                                                    <div className="whitespace-pre-wrap leading-relaxed">
                                                        {(() => {
                                                            let content = msg.content;
                                                            if (typeof content === 'object' && content !== null) {
                                                                content = content.details || content.ai_response?.details || JSON.stringify(content, null, 2);
                                                            }
                                                            if (typeof content === 'string' && content.trim().startsWith('{')) {
                                                                try {
                                                                    const parsed = JSON.parse(content);
                                                                    if (parsed.details) content = parsed.details;
                                                                } catch (e) { }
                                                            }
                                                            // IMAGE DETECTION
                                                            if (typeof content === 'string') {
                                                                const clean = content.trim();
                                                                if ((clean.startsWith('http') && (clean.includes('pollinations.ai') || clean.match(/\.(jpeg|jpg|gif|png)$/))) || clean.startsWith('data:image')) {
                                                                    return (
                                                                        <div className="flex flex-col gap-2">
                                                                            <img
                                                                                src={clean}
                                                                                alt="Generated AI Art"
                                                                                className="rounded-xl border border-white/10 shadow-lg max-w-full h-auto max-h-[400px] object-cover transition-all hover:scale-[1.02]"
                                                                                loading="lazy"
                                                                            />
                                                                            <a href={clean} download="spidy_image.png" target="_blank" rel="noreferrer" className="text-xs text-spidy-primary underline text-center">
                                                                                {clean.startsWith('data:image') ? 'Download Image' : 'Open Full Size'}
                                                                            </a>
                                                                        </div>
                                                                    );
                                                                }
                                                            }
                                                            // UPGRADE 7: Render Markdown properly
                                                            const mdText = typeof content === 'string' ? content.replace(/\\n/g, '\n') : JSON.stringify(content);
                                                            return (
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkGfm]}
                                                                    components={{
                                                                        code({ inline, children }) {
                                                                            return inline
                                                                                ? <code className="bg-black/40 text-spidy-primary px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                                                                                : <pre className="bg-black/40 p-3 rounded-lg text-xs overflow-x-auto my-2 border border-white/5"><code>{children}</code></pre>;
                                                                        },
                                                                        strong({ children }) { return <strong className="text-white font-bold">{children}</strong>; },
                                                                        ul({ children }) { return <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>; },
                                                                        ol({ children }) { return <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>; },
                                                                        a({ href, children }) { return <a href={href} target="_blank" rel="noreferrer" className="text-spidy-primary underline hover:text-red-400">{children}</a>; },
                                                                    }}
                                                                >{mdText}</ReactMarkdown>
                                                            );
                                                        })()}
                                                    </div>
                                                )}
                                            </div>
                                            {/* UPGRADE 9: HH:MM timestamp on hover */}
                                            {msg.timestamp && (
                                                <span className={`absolute -bottom-4 text-[9px] text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity ${msg.role === 'user' ? 'right-0' : 'left-0'}`}>
                                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                            )}
                                        </div>
                                    </motion.div>
                                ))
                            )}

                            {/* UPGRADE 6: Animated 3-dot typing indicator */}
                            {loading && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                                    <div className="bg-white/5 border border-white/5 p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
                                        <span className="flex gap-1">
                                            {[0, 1, 2].map(i => (
                                                <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-spidy-primary"
                                                    animate={{ opacity: [0.3, 1, 0.3] }}
                                                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                                                />
                                            ))}
                                        </span>
                                        <span className="text-xs font-mono text-gray-500">THINKING</span>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                        {/* UPGRADE 8: Auto-scroll anchor */}
                        <div ref={chatEndRef} />
                    </div>
                </div>

                {/* Status Bar */}
                <AnimatePresence>
                    {loading && aiStatus && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="px-4 py-1.5 text-[10px] font-mono font-bold text-spidy-primary bg-spidy-primary/5 border border-spidy-primary/20 rounded-lg self-center flex items-center gap-2 mb-2"
                        >
                            <div className="w-1.5 h-1.5 rounded-full bg-spidy-primary animate-pulse" />
                            SYSTEM_LOG: {aiStatus}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Enhanced Input Area */}
                <div className="p-4 pt-0">
                    <div className={`bg-black/40 backdrop-blur-md rounded-2xl p-2 border transition-all flex flex-col gap-2 relative group focus-within:border-spidy-primary/50 ${selectedFile ? 'border-spidy-primary/50 shadow-lg shadow-spidy-primary/10' : 'border-white/10'}`}>

                        {/* File Preview */}
                        <AnimatePresence>
                            {selectedFile && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="px-3 py-2 flex items-center justify-between bg-spidy-primary/10 rounded-lg mx-2 border border-spidy-primary/20"
                                >
                                    <div className="flex items-center gap-2 text-xs text-spidy-primary font-mono truncate">
                                        <ImageIcon size={14} />
                                        <span>{selectedFile.name} (Attached)</span>
                                    </div>
                                    <button onClick={clearFile} className="text-spidy-primary hover:text-white transition-colors">
                                        <X size={14} />
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <textarea
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), onSend())}
                            placeholder={`Ask Spidy (${modelMode.toUpperCase()} Mode)...`}
                            className="w-full bg-transparent border-none outline-none text-white px-4 py-2 placeholder:text-gray-600 resize-none h-12 text-sm font-medium"
                        />

                        {/* Toolbar */}
                        <div className="flex items-center justify-between px-2 pb-1">
                            <div className="flex items-center gap-1">
                                <input
                                    type="file"
                                    hidden
                                    ref={fileInputRef}
                                    accept="image/*"
                                    onChange={handleFileChange}
                                />
                                <button
                                    className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                                    onClick={handleImageClick}
                                    title="Upload Image"
                                >
                                    <ImageIcon size={18} />
                                </button>
                                <button
                                    className={`p-2 rounded-lg hover:bg-white/10 transition-colors ${isRecording ? 'text-red-500 animate-pulse bg-red-500/10' : 'text-gray-400 hover:text-white'}`}
                                    onClick={toggleVoice}
                                    title="Voice Command"
                                >
                                    <Mic size={18} />
                                </button>
                            </div>

                            <button
                                onClick={onSend}
                                disabled={loading}
                                className={`px-6 py-2 rounded-xl transition-all duration-200 flex items-center gap-2 font-bold text-xs tracking-wide ${loading
                                    ? 'bg-gray-700 cursor-not-allowed text-gray-500'
                                    : 'bg-spidy-primary hover:bg-red-600 text-white shadow-lg shadow-spidy-primary/20 hover:shadow-spidy-primary/40 active:scale-95'}`}
                            >
                                {loading ? 'BUSY' : 'EXECUTE'}
                                {!loading && <Send size={14} />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
