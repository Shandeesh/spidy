import { MessageSquare, TrendingUp, LayoutDashboard, PieChart, Zap } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
    return (
        <div className="w-20 lg:w-64 bg-black/40 backdrop-blur-xl border-r border-white/10 flex flex-col p-4 gap-2">
            <div className="flex items-center gap-3 px-2 py-4 mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-spidy-primary to-orange-600 rounded-lg flex items-center justify-center shadow-lg shadow-spidy-primary/20">
                    <span className="text-xl">🕷️</span>
                </div>
                <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 hidden lg:block">
                    Spidy <span className="text-spidy-primary">AI</span>
                </h1>
            </div>

            <NavButton
                active={activeTab === 'ai'}
                onClick={() => setActiveTab('ai')}
                icon={<MessageSquare size={20} />}
                label="AI Core"
            />

            <NavButton
                active={activeTab === 'trading'}
                onClick={() => setActiveTab('trading')}
                icon={<TrendingUp size={20} />}
                label="Trading Floor"
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
        </div>
    );
}

function NavButton({ active, onClick, icon, label }) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-200 group ${active
                ? 'bg-spidy-primary/20 text-white border border-spidy-primary/30 shadow-lg shadow-spidy-primary/10'
                : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
        >
            <div className={`p-2 rounded-lg transition-colors ${active ? 'bg-spidy-primary' : 'bg-white/5 group-hover:bg-white/10'}`}>
                {icon}
            </div>
            <span className="font-medium hidden lg:block">{label}</span>
        </button>
    );
}
