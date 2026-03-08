import React, { useState, useEffect, useRef } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

export default function RealTimePnLChart({ apiUrl = 'http://localhost:8000' }) {
    const [chartData, setChartData] = useState({
        labels: [],
        datasets: [{
            label: 'Equity',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            fill: true,
            tension: 0.4
        }]
    });

    const [stats, setStats] = useState({
        current: 0,
        change: 0,
        changePercent: 0,
        high: 0,
        low: 0
    });

    const [influxAvailable, setInfluxAvailable] = useState(false);
    const chartRef = useRef(null);

    useEffect(() => {
        // Check if InfluxDB is available
        fetch(`${apiUrl}/influx/status`)
            .then(res => res.json())
            .then(data => {
                setInfluxAvailable(data.connected);
                if (data.connected) {
                    fetchEquityData();
                } else {
                    useFallbackData();
                }
            })
            .catch(() => {
                useFallbackData();
            });

        // Refresh every 10 seconds
        const interval = setInterval(() => {
            if (influxAvailable) {
                fetchEquityData();
            } else {
                useFallbackData();
            }
        }, 10000);

        return () => clearInterval(interval);
    }, [influxAvailable]);

    const fetchEquityData = async () => {
        try {
            const response = await fetch(`${apiUrl}/influx/equity?hours=24`);
            const result = await response.json();

            if (result.data && result.data.length > 0) {
                const times = result.data.map(d => {
                    const date = new Date(d.time);
                    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                });

                const values = result.data.map(d => d.equity);

                // Calculate stats
                const current = values[values.length - 1];
                const initial = values[0];
                const change = current - initial;
                const changePercent = (change / initial) * 100;
                const high = Math.max(...values);
                const low = Math.min(...values);

                setStats({
                    current: current.toFixed(2),
                    change: change.toFixed(2),
                    changePercent: changePercent.toFixed(2),
                    high: high.toFixed(2),
                    low: low.toFixed(2)
                });

                setChartData({
                    labels: times,
                    datasets: [{
                        label: 'Equity',
                        data: values,
                        borderColor: change >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)',
                        backgroundColor: change >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 2
                    }]
                });
            }
        } catch (error) {
            console.error('Failed to fetch equity data:', error);
        }
    };

    const useFallbackData = async () => {
        try {
            const response = await fetch(`${apiUrl}/status`);
            const data = await response.json();

            // Generate simple chart from current equity
            const now = new Date();
            const times = [];
            const values = [];

            for (let i = 23; i >= 0; i--) {
                const time = new Date(now.getTime() - i * 60 * 60 * 1000);
                times.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
                // Simulate slight variation around current equity
                const variance = (Math.random() - 0.5) * (data.equity * 0.02);
                values.push(data.equity + variance);
            }

            const current = data.equity;
            const initial = values[0];
            const change = current - initial;

            setStats({
                current: current.toFixed(2),
                change: change.toFixed(2),
                changePercent: ((change / initial) * 100).toFixed(2),
                high: Math.max(...values).toFixed(2),
                low: Math.min(...values).toFixed(2)
            });

            setChartData({
                labels: times,
                datasets: [{
                    label: 'Equity (Simulated)',
                    data: values,
                    borderColor: 'rgb(147, 51, 234)',
                    backgroundColor: 'rgba(147, 51, 234, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            });
        } catch (error) {
            console.error('Failed to fetch status:', error);
        }
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                display: false
            },
            title: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1
            }
        },
        scales: {
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: 'rgba(255, 255, 255, 0.7)',
                    callback: function (value) {
                        return '$' + value.toLocaleString();
                    }
                }
            },
            x: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: 'rgba(255, 255, 255, 0.7)',
                    maxRotation: 0,
                    autoSkip: true,
                    maxTicksLimit: 12
                }
            }
        }
    };

    return (
        <div className="pnl-chart-container">
            <div className="chart-header">
                <div>
                    <h3 className="chart-title">Equity Performance</h3>
                    {!influxAvailable && (
                        <span className="chart-subtitle">⚠️ InfluxDB unavailable - showing simulated data</span>
                    )}
                </div>
                <div className="chart-stats">
                    <div className="stat-item">
                        <span className="stat-label">Current</span>
                        <span className="stat-value">${stats.current}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Change</span>
                        <span className={`stat-value ${parseFloat(stats.change) >= 0 ? 'positive' : 'negative'}`}>
                            {parseFloat(stats.change) >= 0 ? '+' : ''}${stats.change} ({stats.changePercent}%)
                        </span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">High</span>
                        <span className="stat-value">${stats.high}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Low</span>
                        <span className="stat-value">${stats.low}</span>
                    </div>
                </div>
            </div>

            <div className="chart-canvas">
                <Line ref={chartRef} data={chartData} options={options} />
            </div>

            <style jsx>{`
        .pnl-chart-container {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 20px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 20px;
        }
        
        .chart-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: white;
          margin: 0;
        }
        
        .chart-subtitle {
          font-size: 0.875rem;
          color: rgba(255, 255, 255, 0.6);
          display: block;
          margin-top: 4px;
        }
        
        .chart-stats {
          display: flex;
          gap: 24px;
          flex-wrap: wrap;
        }
        
        .stat-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .stat-label {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .stat-value {
          font-size: 1.125rem;
          font-weight: 600;
          color: white;
        }
        
        .stat-value.positive {
          color: rgb(34, 197, 94);
        }
        
        .stat-value.negative {
          color: rgb(239, 68, 68);
        }
        
        .chart-canvas {
          height: 300px;
          position: relative;
        }
        
        @media (max-width: 768px) {
          .chart-header {
            flex-direction: column;
          }
          
          .chart-stats {
            width: 100%;
            justify-content: space-between;
          }
          
          .chart-canvas {
            height: 250px;
          }
        }
      `}</style>
        </div>
    );
}
