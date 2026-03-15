import React, { useMemo } from 'react';
import { Settings2, Zap, Shield, HelpCircle } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

interface TuningPanelProps {
    lambda: number;
    setLambda: (val: number) => void;
}

const TuningPanel: React.FC<TuningPanelProps> = ({ lambda, setLambda }) => {
    // Generate mock chart data based on lambda
    const chartData = useMemo(() => {
        const data = [];
        for (let i = 0; i <= 5000; i += 500) {
            const isCurrent = Math.abs(i - lambda) < 250;

            data.push({
                lambdaValue: i,
                safeCost: 10 + (i / 100), // Safety priority cost metric
                fastCost: 100 - (i / 50), // Speed priority tradeoff
                isCurrent // (Optional) Can be used for custom point rendering
            });
        }
        return data;
    }, [lambda]);

    return (
        <div className="w-96 bg-zinc-950/90 backdrop-blur-xl border-l border-zinc-800 shadow-2xl flex flex-col h-full z-20">
            <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                        <Settings2 className="w-5 h-5 text-blue-500" />
                        <span>Optimization Engine</span>
                    </h2>
                    <p className="text-zinc-400 text-sm mt-1">Live Algorithm Tuning</p>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-8">

                {/* Slider Control */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center mb-2">
                        <h3 className="text-white font-medium flex items-center space-x-2">
                            <span>Safety Priority Modifier (λ)</span>
                            <HelpCircle className="w-4 h-4 text-zinc-500 hover:text-blue-400 cursor-help" />
                        </h3>
                        <span className="bg-blue-600/20 text-blue-400 text-xs font-bold px-2 py-1 rounded-md border border-blue-500/30">
                            {lambda}
                        </span>
                    </div>

                    <input
                        type="range"
                        min="0"
                        max="5000"
                        step="100"
                        value={lambda}
                        onChange={(e) => setLambda(Number(e.target.value))}
                        className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />

                    <div className="flex justify-between text-xs text-zinc-500 font-medium">
                        <span className="flex items-center space-x-1"><Zap className="w-3 h-3 text-amber-500" /> <span>Bias Fast (0)</span></span>
                        <span className="flex items-center space-x-1"><span>Bias Safe (5k)</span> <Shield className="w-3 h-3 text-emerald-500" /></span>
                    </div>
                </div>

                {/* Tradeoff Visualization */}
                <div className="space-y-4 pt-6 border-t border-zinc-900">
                    <h3 className="text-white font-medium">Cost Function Tradeoff</h3>
                    <p className="text-xs text-zinc-500 leading-relaxed mb-4">
                        Visualizing the impact of the current λ parameter on the cost function.
                    </p>

                    <div className="h-48 w-full bg-zinc-900/50 rounded-xl p-3 border border-zinc-800 shadow-inner">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorFast" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="lambdaValue" tick={{ fontSize: 10, fill: '#71717a' }} stroke="#3f3f46" />
                                <YAxis tick={{ fontSize: 10, fill: '#71717a' }} stroke="#3f3f46" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px' }}
                                    itemStyle={{ fontSize: '12px' }}
                                    labelStyle={{ color: '#a1a1aa', fontSize: '10px' }}
                                />
                                <Area type="monotone" dataKey="safeCost" name="Safety Cost" stroke="#10b981" fillOpacity={1} fill="url(#colorSafe)" />
                                <Area type="monotone" dataKey="fastCost" name="Speed Cost" stroke="#f59e0b" fillOpacity={1} fill="url(#colorFast)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Global Impact Summary */}
                <div className="bg-zinc-900 rounded-xl p-4 border border-zinc-800">
                    <h4 className="text-sm font-semibold text-white mb-3">Estimated Impact</h4>
                    <div className="space-y-3">
                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-zinc-400">Avg. Route Deviation</span>
                                <span className="text-white font-medium">+{Math.round(lambda / 500)}%</span>
                            </div>
                            <div className="w-full bg-zinc-800 rounded-full h-1.5">
                                <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min((lambda / 5000) * 100, 100)}%` }}></div>
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-zinc-400">Avoidance Aggressiveness</span>
                                <span className="text-emerald-400 font-medium">{lambda > 2500 ? 'High' : lambda > 1000 ? 'Medium' : 'Low'}</span>
                            </div>
                            <div className="w-full bg-zinc-800 rounded-full h-1.5">
                                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${Math.min((lambda / 5000) * 100, 100)}%` }}></div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            <div className="p-4 border-t border-zinc-800">
                <button className="w-full bg-blue-600 hover:bg-blue-500 transition-colors text-white font-medium py-3 rounded-xl shadow-[0_0_20px_rgba(37,99,235,0.3)]">
                    Deploy to Production
                </button>
            </div>
        </div>
    );
};

export default TuningPanel;