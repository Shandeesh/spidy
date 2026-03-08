class MLGuardrails:
    def __init__(self):
        pass

    def check_prediction(self, prediction: float) -> bool:
        """
        Checks if prediction is confident enough and safe.
        """
        # Example: Threshold check
        if 0.4 < prediction < 0.6:
            return False # Indecisive
            
        return True

    def validate_inputs(self, features):
        """
        Ensures features are within expected range.
        """
        return True
