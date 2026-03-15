import React from 'react';
import { Map, AlertTriangle, Settings, ShieldAlert } from 'lucide-react';

interface SidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
    const navItems = [
        { id: 'map', label: 'Live Map', icon: Map },
        { id: 'reports', label: 'Incident Reports', icon: AlertTriangle },
        { id: 'tuning', label: 'Algorithm Tuning', icon: Settings },
    ];

    return (
        <aside className="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col h-full z-10 shrink-0 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
            {/* Branding */}
            <div className="p-6 border-b border-zinc-800/60 flex items-center space-x-3">
                <div className="bg-blue-600 p-2 rounded-lg shadow-[0_0_15px_rgba(37,99,235,0.4)]">
                    <ShieldAlert className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-bold text-white tracking-wide">SafeRoute</h1>
                    <p className="text-xs text-zinc-400 font-medium">City Command Center</p>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-6 px-4 space-y-2">
                {navItems.map((item) => {
                    const isActive = activeTab === item.id;
                    const Icon = item.icon;

                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 group
                ${isActive
                                    ? 'bg-blue-600/10 border border-blue-500/30 text-blue-400 shadow-[inset_0px_0px_20px_rgba(37,99,235,0.1)]'
                                    : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent'
                                }
              `}
                        >
                            <Icon
                                className={`w-5 h-5 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`}
                            />
                            <span className="font-medium">{item.label}</span>
                        </button>
                    );
                })}
            </nav>

            {/* Footer / User Profile Mock */}
            <div className="p-4 border-t border-zinc-800/60 m-4 rounded-xl bg-zinc-900/50 backdrop-blur-md flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 border-2 border-zinc-800 flex items-center justify-center text-sm font-bold shadow-lg">
                    AD
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">Administrator</p>
                    <p className="text-xs text-zinc-500 truncate">System Operator</p>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
