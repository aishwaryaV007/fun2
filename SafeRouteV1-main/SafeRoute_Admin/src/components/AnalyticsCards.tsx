import React from 'react';
import { Users, AlertCircle, Radio } from 'lucide-react';

interface AnalyticsCardsProps {
    activeUsers: number;
    sosAlertCount: number;
}

const AnalyticsCards: React.FC<AnalyticsCardsProps> = ({ activeUsers, sosAlertCount }) => {
    const kpis = [
        {
            title: 'Active Users',
            value: activeUsers.toString(),
            subtitle: 'Connected right now',
            icon: Users,
            color: 'text-blue-500',
            bg: 'bg-blue-500/10 border-blue-500/20',
            live: true,
        },
        {
            title: 'High-Risk Zones',
            value: '24',
            subtitle: 'Identified in Hyderabad',
            icon: AlertCircle,
            color: 'text-rose-500',
            bg: 'bg-rose-500/10 border-rose-500/20',
            live: false,
        },
        {
            title: 'SOS Alerts',
            value: sosAlertCount.toString(),
            subtitle: 'In this session',
            icon: Radio,
            color: 'text-amber-500',
            bg: 'bg-amber-500/10 border-amber-500/20',
            live: true,
        },
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 z-20 relative px-6 pt-6">
            {kpis.map((kpi, index) => {
                const Icon = kpi.icon;
                return (
                    <div
                        key={index}
                        className={`rounded-2xl border bg-zinc-900/80 backdrop-blur-sm p-5 shadow-lg transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${kpi.bg}`}
                    >
                        <div className="flex justify-between items-start">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <p className="text-zinc-400 text-sm font-medium">{kpi.title}</p>
                                    {kpi.live && (
                                        <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block"></span>
                                            LIVE
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-3xl font-bold text-white tracking-tight">{kpi.value}</h3>
                            </div>
                            <div className={`p-3 rounded-xl ${kpi.bg.split(' ')[0]}`}>
                                <Icon className={`w-6 h-6 ${kpi.color}`} />
                            </div>
                        </div>
                        <div className="mt-4 flex items-center space-x-2 text-sm">
                            <span className="text-zinc-500">{kpi.subtitle}</span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default AnalyticsCards;
