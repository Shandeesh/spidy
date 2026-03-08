import numpy as np
import pandas as pd

class PSIDriftDetector:
    """
    Detects feature drift using Population Stability Index (PSI).
    Compares the distribution of a feature in a baseline window vs current window.
    """
    
    def calculate_psi(self, expected, actual, bucket_type='bins', buckets=10, axis=0):
        """
        Calculate the PSI (Population Stability Index) for a single feature.
        
        Args:
            expected (array-like): Baseline data.
            actual (array-like): Current data.
            buckets (int): Number of bins.
            
        Returns:
            float: PSI value.
        """
        def scale_range(input, min, max):
            input += (1e-6) # Avoid zero
            input /= (1e-6 + max - min)
            input *= (buckets - 1)
            return input

        breakpoints = np.linspace(0, buckets, buckets + 1)
        
        # Simple binning logic assumption for numeric features
        # In prod, we'd use robust binning based on percentiles of 'expected'
        
        # Aligning distributions for simple PSI
        # We need to bin 'expected' and get percentages
        expected_percents = np.histogram(expected, bins=buckets)[0] / len(expected)
        
        # Use same bins for 'actual' - wait, numpy histogram returns edges.
        # We should use expected edges for actual.
        exp_vals, bins = np.histogram(expected, bins=buckets)
        expected_percents = exp_vals / len(expected)
        
        act_vals, _ = np.histogram(actual, bins=bins)
        actual_percents = act_vals / len(actual)

        # Avoid division by zero
        expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
        actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
        
        psi_values = (expected_percents - actual_percents) * np.log(expected_percents / actual_percents)
        psi = np.sum(psi_values)
        
        return psi

    def check_drift(self, baseline_df, current_df, threshold=0.25):
        """
        Check all columns for drift.
        """
        drift_report = {}
        drift_detected = False
        
        common_cols = set(baseline_df.columns).intersection(set(current_df.columns))
        
        for col in common_cols:
            # Skip non-numeric
            if not np.issubdtype(baseline_df[col].dtype, np.number):
                continue
                
            psi = self.calculate_psi(baseline_df[col].values, current_df[col].values)
            
            status = "OK"
            if psi > threshold:
                status = "DRIFT"
                drift_detected = True
            elif psi > 0.1:
                status = "WARNING"
                
            drift_report[col] = {"psi": psi, "status": status}
            
        return drift_detected, drift_report
