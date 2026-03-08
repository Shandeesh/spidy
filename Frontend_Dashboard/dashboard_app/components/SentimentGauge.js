import React, { useState, useEffect } from 'react';

export default function SentimentGauge({ apiUrl = 'http://localhost:8000' }) {
    const [sentiment, setSentiment] = useState({
        label: 'NEUTRAL',
        score: 0,
        updated: null
    });

    useEffect(() => {
        fetchSentiment();
        const interval = setInterval(fetchSentiment, 30000); // Every 30s
        return () => clearInterval(interval);
    }, []);

    const fetchSentiment = async () => {
        try {
            const response = await fetch(`${apiUrl}/status`);
            const data = await response.json();

            setSentiment({
                label: data.sentiment || 'NEUTRAL',
                score: data.sentiment_score || 0,
                updated: new Date()
            });
        } catch (error) {
            console.error('Failed to fetch sentiment:', error);
        }
    };

    const getGaugeColor = () => {
        if (sentiment.label === 'BULLISH') return '#22c55e';
        if (sentiment.label === 'BEARISH') return '#ef4444';
        return '#8b5cf6';
    };

    const getRotation = () => {
        // Map score from -1 to +1 to -90deg to +90deg
        return sentiment.score * 90;
    };

    return (
        <div className="sentiment-gauge-container">
            <h4 className="gauge-title">Market Sentiment</h4>

            <div className="gauge-visual">
                <svg width="200" height="120" viewBox="0 0 200 120">
                    {/* Background arc */}
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke="rgba(255, 255, 255, 0.1)"
                        strokeWidth="20"
                        strokeLinecap="round"
                    />

                    {/* Colored zones */}
                    <path
                        d="M 20 100 A 80 80 0 0 1 100 20"
                        fill="none"
                        stroke="rgba(239, 68, 68, 0.3)"
                        strokeWidth="18"
                        strokeLinecap="round"
                    />
                    <path
                        d="M 100 20 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke="rgba(34, 197, 94, 0.3)"
                        strokeWidth="18"
                        strokeLinecap="round"
                    />

                    {/* Needle */}
                    <g transform={`rotate(${getRotation()}, 100, 100)`}>
                        <line
                            x1="100"
                            y1="100"
                            x2="100"
                            y2="35"
                            stroke={getGaugeColor()}
                            strokeWidth="3"
                            strokeLinecap="rounded"
                            style={{ transition: 'all 1s ease' }}
                        />
                        <circle
                            cx="100"
                            cy="100"
                            r="6"
                            fill={getGaugeColor()}
                        />
                    </g>

                    {/* Labels */}
                    <text x="20" y="115" fill="rgba(255, 255, 255, 0.6)" fontSize="10" textAnchor="start">BEARISH</text>
                    <text x="100" y="25" fill="rgba(255, 255, 255, 0.6)" fontSize="10" textAnchor="middle">NEUTRAL</text>
                    <text x="180" y="115" fill="rgba(255, 255, 255, 0.6)" fontSize="10" textAnchor="end">BULLISH</text>
                </svg>
            </div>

            <div className="sentiment-info">
                <div className="sentiment-label" style={{ color: getGaugeColor() }}>
                    {sentiment.label}
                </div>
                <div className="sentiment-score">
                    Score: {sentiment.score.toFixed(2)}
                </div>
                {sentiment.updated && (
                    <div className="sentiment-updated">
                        Updated: {sentiment.updated.toLocaleTimeString()}
                    </div>
                )}
            </div>

            <style jsx>{`
        .sentiment-gauge-container {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 20px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          text-align: center;
        }
        
        .gauge-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: white;
          margin: 0 0 20px 0;
        }
        
        .gauge-visual {
          display: flex;
          justify-content: center;
          margin-bottom: 16px;
        }
        
        .sentiment-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .sentiment-label {
          font-size: 1.5rem;
          font-weight: 700;
          letter-spacing: 1px;
          text-transform: uppercase;
        }
        
        .sentiment-score {
          font-size: 0.875rem;
          color: rgba(255, 255, 255, 0.7);
        }
        
        .sentiment-updated {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.5);
        }
      `}</style>
        </div>
    );
}
