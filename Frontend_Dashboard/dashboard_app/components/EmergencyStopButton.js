import React, { useState } from 'react';

export default function EmergencyStopButton({ apiUrl = 'http://localhost:8000' }) {
    const [isActive, setIsActive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [confirmation, setConfirmation] = useState(false);

    const handleEmergencyStop = async () => {
        if (!confirmation) {
            setConfirmation(true);
            setTimeout(() => setConfirmation(false), 5000); // Reset after 5s
            return;
        }

        setLoading(true);

        try {
            // Close all positions
            const closeResponse = await fetch(`${apiUrl}/close_all_trades`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profitable_only: false })
            });

            if (closeResponse.ok) {
                setIsActive(true);
                setConfirmation(false);

                // Show success notification
                setTimeout(() => {
                    alert('🚨 EMERGENCY STOP ACTIVATED!\n✅ All positions closed\n⚠️ Auto-trading disabled');
                }, 500);
            }
        } catch (error) {
            console.error('Emergency stop failed:', error);
            alert('❌ Emergency stop failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setIsActive(false);
        setConfirmation(false);
    };

    return (
        <div className="emergency-stop-container">
            {isActive ? (
                <div className="stop-active">
                    <div className="stop-icon pulsing">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                            <rect x="6" y="6" width="12" height="12" fill="currentColor" rx="2" />
                        </svg>
                    </div>
                    <div className="stop-info">
                        <h4>Emergency Stop Active</h4>
                        <p>All trading operations halted</p>
                        <button onClick={handleReset} className="reset-button">
                            Resume Trading
                        </button>
                    </div>
                </div>
            ) : (
                <button
                    className={`emergency-button ${confirmation ? 'confirm-mode' : ''} ${loading ? 'loading' : ''}`}
                    onClick={handleEmergencyStop}
                    disabled={loading}
                >
                    <div className="button-content">
                        <div className="button-icon">
                            {loading ? (
                                <div className="spinner"></div>
                            ) : (
                                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                                    <path
                                        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h2v-6h-2v6zm0-8h2V7h-2v2z"
                                        fill="currentColor"
                                    />
                                </svg>
                            )}
                        </div>
                        <div className="button-text">
                            <span className="button-label">
                                {loading ? 'STOPPING...' : confirmation ? 'CLICK TO CONFIRM' : 'EMERGENCY STOP'}
                            </span>
                            {!loading && !confirmation && (
                                <span className="button-subtitle">Close all positions & halt trading</span>
                            )}
                            {confirmation && (
                                <span className="button-subtitle warning">⚠️ This will close ALL open trades</span>
                            )}
                        </div>
                    </div>
                </button>
            )}

            <style jsx>{`
        .emergency-stop-container {
          background: linear-gradient(135deg, rgba(220, 38, 38, 0.1), rgba(127, 29, 29, 0.1));
          border-radius: 16px;
          padding: 24px;
          border: 2px solid rgba(220, 38, 38, 0.3);
          backdrop-filter: blur(10px);
        }
        
        .emergency-button {
          width: 100%;
          background: linear-gradient(135deg, #dc2626, #991b1b);
          border: none;
          border-radius: 12px;
          padding: 20px;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 20px rgba(220, 38, 38, 0.4);
          position: relative;
          overflow: hidden;
        }
        
        .emergency-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 30px rgba(220, 38, 38, 0.6);
        }
        
        .emergency-button:active:not(:disabled) {
          transform: translateY(0);
        }
        
        .emergency-button.confirm-mode {
          background: linear-gradient(135deg, #facc15, #ca8a04);
          animation: pulse 1s infinite;
        }
        
        .emergency-button.loading {
          opacity: 0.7;
          cursor: not-allowed;
        }
        
        @keyframes pulse {
          0%, 100% {
            box-shadow: 0 4px 20px rgba(250, 204, 21, 0.4);
          }
          50% {
            box-shadow: 0 8px 40px rgba(250, 204, 21, 0.8);
          }
        }
        
        .button-content {
          display: flex;
          align-items: center;
          gap: 16px;
          color: white;
        }
        
        .button-icon {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 50%;
        }
        
        .button-text {
          flex: 1;
          text-align: left;
        }
        
        .button-label {
          display: block;
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: 1px;
        }
        
        .button-subtitle {
          display: block;
          font-size: 0.875rem;
          opacity: 0.9;
          margin-top: 4px;
        }
        
        .button-subtitle.warning {
          font-weight: 600;
          animation: blink 1s infinite;
        }
        
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .stop-active {
          display: flex;
          align-items: center;
          gap: 20px;
          color: white;
        }
        
        .stop-icon {
          width: 60px;
          height: 60px;
          background: rgba(220, 38, 38, 0.2);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #dc2626;
        }
        
        .stop-icon.pulsing {
          animation: pulse-icon 2s infinite;
        }
        
        @keyframes pulse-icon {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.1);
            opacity: 0.8;
          }
        }
        
        .stop-info h4 {
          margin: 0 0 8px 0;
          font-size: 1.25rem;
          font-weight: 600;
        }
        
        .stop-info p {
          margin: 0 0 16px 0;
          color: rgba(255, 255, 255, 0.8);
        }
        
        .reset-button {
          background: linear-gradient(135deg, #3b82f6, #1d4ed8);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        
        .reset-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
      `}</style>
        </div>
    );
}
