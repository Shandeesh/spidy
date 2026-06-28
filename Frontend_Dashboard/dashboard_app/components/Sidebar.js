import { MessageSquare, TrendingUp, PieChart, Zap, Settings, Paintbrush } from 'lucide-react';
import React, { useState } from 'react';

export default function Sidebar({ activeTab, setActiveTab, mt5Status, currentTheme, onThemeChange }) {
    const hasPositions = mt5Status?.positions?.length > 0;
    const isConnected = mt5Status?.connected;
    const dotColor = hasPositions ? 'bg-green-400' : isConnected ? 'bg-blue-400' : 'bg-red-400';
    const [showThemes, setShowThemes] = useState(false);

    const themes = [
        { name: 'Cyberpunk', class: 'theme-cyberpunk', emoji: '⚡' },
        { name: 'Corporate', class: 'theme-corporate', emoji: '💼' },
        { name: 'Nature', class: 'theme-nature', emoji: '🍃' },
        { name: 'Retro', class: 'theme-retro', emoji: '👾' },
        { name: 'Ocean', class: 'theme-ocean', emoji: '🌊' },
        { name: 'Maoism Glass', class: 'theme-liquid-glass-maoism', emoji: '★' },
    ];

    const activeThemeObj = themes.find(t => t.class === currentTheme) || themes[0];

    return (
        <div className="w-20 lg:w-64 bg-black/40 backdrop-blur-xl border-r border-white/10 flex flex-col p-4 gap-2 relative">
            <div className="flex items-center gap-3 px-2 py-4 mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-spidy-primary to-orange-600 rounded-lg flex items-center justify-center shadow-lg shadow-spidy-primary/20">
                    <span className="text-xl">🕷️</span>
                </div>
                <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 hidden lg:block">
                    Spidy <span className="text-spidy-primary">AI</span>
                </h1>
            </div>

            {/* Trading Floor — First & default */}
            <NavButton
                active={activeTab === 'trading'}
                onClick={() => setActiveTab('trading')}
                icon={<TrendingUp size={20} />}
                label="Trading Floor"
                dotColor={dotColor}
            />

            <NavButton
                active={activeTab === 'ai'}
                onClick={() => setActiveTab('ai')}
                icon={<MessageSquare size={20} />}
                label="AI Core"
            />

            <NavButton
                active={activeTab === 'finance'}
                onClick={() => setActiveTab('finance')}
                icon={<PieChart size={20} />}
                label="Financial Assistant"
            />

            <NavButton
                active={activeTab === 'shoonga'}
                onClick={() => setActiveTab('shoonga')}
                icon={<Zap size={20} />}
                label="Shoonga"
            />

            <NavButton
                active={activeTab === 'control_center'}
                onClick={() => setActiveTab('control_center')}
                icon={<Settings size={20} />}
                label="Control Center"
            />

            {/* Spacer */}
            <div className="flex-1" />

            {/* Theme Switcher */}
            {onThemeChange && (
                <div className="border-t border-white/10 pt-4 flex flex-col gap-2 relative">
                    <button
                        onClick={() => setShowThemes(!showThemes)}
                        className="flex items-center gap-3 p-3 rounded-xl transition-all duration-200 text-gray-400 hover:bg-white/5 hover:text-white w-full text-left"
                    >
                        <div className="p-2 rounded-lg bg-white/5 text-spidy-accent">
                            <Paintbrush size={20} />
                        </div>
                        <div className="hidden lg:flex flex-col flex-1">
                            <span className="text-[10px] uppercase font-bold text-gray-500">Theme</span>
                            <span className="text-xs text-white font-medium">{activeThemeObj.name}</span>
                        </div>
                    </button>

                    {showThemes && (
                        <div className="absolute bottom-16 left-4 right-4 lg:left-0 lg:right-0 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-2xl p-2 shadow-2xl flex flex-col gap-1 z-50">
                            <p className="text-[9px] uppercase font-bold text-gray-500 px-3 py-1">Select Theme</p>
                            {themes.map(t => (
                                <button
                                    key={t.class}
                                    onClick={() => {
                                        onThemeChange(t.class);
                                        setShowThemes(false);
                                    }}
                                    className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs transition-all w-full text-left ${currentTheme === t.class ? 'bg-spidy-primary/20 text-white font-bold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
                                >
                                    <span>{t.emoji}</span>
                                    <span>{t.name}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function NavButton({ active, onClick, icon, label, dotColor }) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-200 group relative ${active
                ? 'bg-spidy-primary/20 text-white border border-spidy-primary/30 shadow-lg shadow-spidy-primary/10'
                : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
        >
            <div className={`p-2 rounded-lg transition-colors relative ${active ? 'bg-spidy-primary' : 'bg-white/5 group-hover:bg-white/10'}`}>
                {icon}
                {dotColor && (
                    <span className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${dotColor} shadow-sm animate-pulse`} />
                )}
            </div>
            <span className="font-medium hidden lg:block">{label}</span>
        </button>
    );
}
