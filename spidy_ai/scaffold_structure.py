import os

# Define the full structure map
STRUCTURE = {
    "data_feed": ["shoonya_feed.py"],
    "feature_engineering": ["volume_features.py"],
    "regime_detection": ["regime_rules.py"],
    "strategies/trend": ["supertrend.py", "adx_filter.py", "ichimoku.py"],
    "strategies/momentum": ["stochastic_rsi.py", "williams_r.py", "cci.py", "pivot_points.py"],
    "strategies/volatility": ["donchian.py", "bollinger_squeeze.py", "keltner.py"],
    "ml/models": ["lstm_mid.py"],
    "ml/ensemble": ["ml_weights.py"],
    "ml/training": ["offline_trainer.py", "retrainer.py"],
    "ml/drift_detection": ["drift_monitor.py"],
    "ml": ["ml_guardrails.py"],
    "risk_management": ["stop_loss.py", "drawdown_guard.py"],
    "execution": ["slippage_model.py", "execution_guard.py"],
    "monitoring": ["trade_logger.py", "performance_tracker.py", "kill_switch.py"],
    "dashboard": ["system_view.py", "ml_view.py", "regime_view.py"],
    "backtesting": ["metrics.py"],
    "utils": ["logger.py", "time_utils.py", "math_utils.py"]
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_structure():
    print("🏗️ Scaffolding Missing Files...")
    
    for folder, files in STRUCTURE.items():
        folder_path = os.path.join(BASE_DIR, *folder.split("/"))
        
        if not os.path.exists(folder_path):
             os.makedirs(folder_path)
             print(f"   Created Directory: {folder}")
             
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    f.write(f"# Spidy AI - {filename}\n")
                    f.write("# Placeholder for Spec Compliance\n\n")
                    f.write("class Placeholder:\n    pass\n")
                print(f"   Created File: {folder}/{filename}")
            else:
                pass
                # print(f"   Exists: {folder}/{filename}")

    print("✅ Structure Complete.")

if __name__ == "__main__":
    create_structure()
