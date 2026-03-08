class OnlineTrainer:
    """
    Manages the online learning loop.
    Buffers labeled trade data and updates models incrementally.
    """
    def __init__(self, xgb_model, buffer_size=100):
        self.xgb_model = xgb_model
        self.buffer_size = buffer_size
        self.feature_buffer = []
        self.label_buffer = []

    def add_sample(self, features, label):
        """
        Add a closed trade result to the buffer.
        
        Args:
            features (list/array): The feature vector used for prediction.
            label (int): 1 if profitable (BUY success) or -1 if loss (or reversed).
                         Typically 1 for "Correct", 0 for "Wrong" in classification?
                         Or if predicting Direction: 1 (Up), 0 (Down).
                         Let's assume our XGBoost predicts Direction (1=Buy, 0=Neutral/Sell class).
                         We need to map Trade PnL to the target class.
        """
        # If we bought (Direction 1) and won -> Label 1
        # If we bought (Direction 1) and lost -> Label 0 (should have been sell/neutral)
        # This requires knowing what the Original Action was. 
        # For simplicity here, we assume 'label' is the "Correct Class".
        
        self.feature_buffer.append(features)
        self.label_buffer.append(label)

        if len(self.feature_buffer) >= self.buffer_size:
            self.trigger_update()

    def trigger_update(self):
        """
        Update the model with buffered data.
        """
        import numpy as np
        
        X = np.array(self.feature_buffer)
        y = np.array(self.label_buffer)
        
        print(f"[OnlineTrainer] Updating XGBoost with {len(X)} samples...")
        try:
            self.xgb_model.online_update(X, y)
            print("[OnlineTrainer] Update success.")
        except Exception as e:
            print(f"[OnlineTrainer] Update failed: {e}")
            
        # Clear buffer
        self.feature_buffer = []
        self.label_buffer = []
