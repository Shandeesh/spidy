class EnsembleEngine:
    def __init__(self):
        self.models = {}
        self.weights = {}

    def add_model(self, name, model, weight=1.0):
        self.models[name] = model
        self.weights[name] = weight

    def get_ensemble_prediction(self, features):
        """
        Returns weighted average of predictions.
        """
        total_weight = sum(self.weights.values())
        if total_weight == 0:
            return 0.5
            
        weighted_sum = 0
        for name, model in self.models.items():
            pred = model.predict(features)
            # Assuming pred is a scalar or we take first element
            val = pred[0] if isinstance(pred, list) else pred
            weighted_sum += val * self.weights[name]
            
        return weighted_sum / total_weight
