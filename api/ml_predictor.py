"""
ML-based Travel Time Predictor
Predicts travel time based on distance, traffic conditions, and historical patterns
"""
import numpy as np
import pickle
import os
from datetime import datetime
from typing import Dict, List, Tuple
import json


class TravelTimePredictor:
    """
    Machine Learning model for predicting travel time with traffic consideration
    Uses a trained model or falls back to heuristic-based prediction
    """
    
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'travel_time_model.pkl')
        self.load_model()
    
    def load_model(self):
        """Load pre-trained model if exists"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                print("✓ Travel time prediction model loaded")
            else:
                print("⚠ No pre-trained model found, using heuristic prediction")
        except Exception as e:
            print(f"⚠ Error loading model: {e}, using heuristic prediction")
            self.model = None
    
    def predict_travel_time(
        self, 
        distance_km: float, 
        traffic_conditions: List[Dict],
        time_of_day: datetime = None
    ) -> Dict:
        """
        Predict travel time based on distance and traffic conditions
        
        Args:
            distance_km: Distance in kilometers
            traffic_conditions: List of traffic data for route segments
            time_of_day: Time of day for prediction (default: now)
        
        Returns:
            Dictionary with predicted time, confidence, and breakdown
        """
        if time_of_day is None:
            time_of_day = datetime.now()
        
        # Calculate average traffic metrics
        avg_congestion = self._calculate_average_congestion(traffic_conditions)
        avg_speed = self._calculate_average_speed(traffic_conditions)
        
        # Get time-of-day factor
        time_factor = self._get_time_of_day_factor(time_of_day)
        
        # Use ML model if available, otherwise use heuristic
        if self.model is not None:
            predicted_time = self._ml_predict(distance_km, avg_congestion, avg_speed, time_factor)
        else:
            predicted_time = self._heuristic_predict(distance_km, avg_congestion, avg_speed, time_factor)
        
        # Validate predicted time
        if np.isnan(predicted_time) or predicted_time <= 0:
            predicted_time = (distance_km / 40.0) * 60  # Fallback: 40 km/h
            
        # Calculate confidence based on traffic variability
        confidence = self._calculate_confidence(traffic_conditions)
        
        # Validate other metrics
        if np.isnan(avg_speed) or avg_speed <= 0:
            avg_speed = 40.0
        if np.isnan(avg_congestion):
            avg_congestion = 0.0
        
        # Calculate time range (min/max)
        time_range = self._calculate_time_range(predicted_time, confidence)
        
        def safe_float(val, precision=1):
            if val is None or np.isnan(val) or np.isinf(val):
                return 0.0
            return float(round(val, precision))
            
        def safe_int(val):
            if val is None or np.isnan(val) or np.isinf(val):
                return 0
            return int(round(val))
        
        return {
            'predicted_time_minutes': safe_float(predicted_time, 1),
            'predicted_time_seconds': safe_int(predicted_time * 60),
            'min_time_minutes': safe_float(time_range['min'], 1),
            'max_time_minutes': safe_float(time_range['max'], 1),
            'confidence': safe_float(confidence * 100, 1),
            'average_speed_kmh': safe_float(avg_speed, 1),
            'average_congestion_percent': safe_float(avg_congestion, 1),
            'time_of_day_factor': safe_float(time_factor, 2),
            'breakdown': {
                'base_time': safe_float(distance_km / 50 * 60, 1),
                'traffic_delay': safe_float(predicted_time - (distance_km / 50 * 60), 1),
                'distance_km': safe_float(distance_km, 2)
            }
        }
    
    def _calculate_average_congestion(self, traffic_conditions: List[Dict]) -> float:
        """Calculate weighted average congestion"""
        if not traffic_conditions:
            return 0.0
        
        total_congestion = sum(tc.get('congestion_percentage', 0) for tc in traffic_conditions)
        return total_congestion / len(traffic_conditions)
    
    def _calculate_average_speed(self, traffic_conditions: List[Dict]) -> float:
        """Calculate weighted average speed"""
        if not traffic_conditions:
            return 50.0  # Default speed
        
        total_speed = sum(tc.get('average_speed', 50) for tc in traffic_conditions)
        return total_speed / len(traffic_conditions)
    
    def _get_time_of_day_factor(self, time_of_day: datetime) -> float:
        """
        Get traffic multiplier based on time of day
        Rush hours: 7-9 AM, 5-7 PM = higher factor
        Night: 11 PM - 6 AM = lower factor
        """
        hour = time_of_day.hour
        
        # Rush hour morning (7-9 AM)
        if 7 <= hour < 9:
            return 1.3
        # Rush hour evening (5-7 PM)
        elif 17 <= hour < 19:
            return 1.4
        # Late evening/night (11 PM - 6 AM)
        elif hour >= 23 or hour < 6:
            return 0.8
        # Regular hours
        else:
            return 1.0
    
    def _ml_predict(self, distance_km: float, avg_congestion: float, 
                    avg_speed: float, time_factor: float) -> float:
        """Predict using ML model"""
        # Feature vector: [distance, congestion, speed, time_factor]
        features = np.array([[distance_km, avg_congestion, avg_speed, time_factor]])
        
        try:
            predicted_minutes = self.model.predict(features)[0]
            return max(1.0, predicted_minutes)  # Minimum 1 minute
        except Exception as e:
            print(f"ML prediction failed: {e}, falling back to heuristic")
            return self._heuristic_predict(distance_km, avg_congestion, avg_speed, time_factor)
    
    def _heuristic_predict(self, distance_km: float, avg_congestion: float,
                          avg_speed: float, time_factor: float) -> float:
        """
        Heuristic-based prediction using traffic-adjusted speed
        This is a sophisticated formula based on real-world traffic patterns
        """
        # Base speed (ideal conditions)
        base_speed = 50.0  # km/h for Bishkek city
        
        # Adjust speed based on congestion
        # Congestion reduces speed exponentially
        congestion_factor = 1 - (avg_congestion / 100) * 0.7  # Max 70% reduction
        
        # If we have actual average speed from traffic data, use it
        if avg_speed > 0:
            effective_speed = avg_speed * congestion_factor
        else:
            effective_speed = base_speed * congestion_factor
        
        # Apply time of day factor
        effective_speed = effective_speed / time_factor
        
        # Ensure minimum speed (even in worst traffic)
        effective_speed = max(10.0, effective_speed)
        
        # Calculate time in minutes
        time_minutes = (distance_km / effective_speed) * 60
        
        # Add fixed delay for stops, turns, etc. (1 min per 2 km)
        fixed_delay = distance_km * 0.5
        
        total_time = time_minutes + fixed_delay
        
        return max(1.0, total_time)
    
    def _calculate_confidence(self, traffic_conditions: List[Dict]) -> float:
        """
        Calculate prediction confidence based on traffic variability
        Returns value between 0 and 1
        """
        if not traffic_conditions or len(traffic_conditions) < 2:
            return 0.7  # Default moderate confidence
        
        # Calculate standard deviation of congestion
        congestions = [tc.get('congestion_percentage', 0) for tc in traffic_conditions]
        std_dev = np.std(congestions)
        
        # Lower std_dev = higher confidence
        # Normalize: std_dev of 0 = 1.0 confidence, std_dev of 50 = 0.5 confidence
        confidence = max(0.5, 1.0 - (std_dev / 100))
        
        return confidence
    
    def _calculate_time_range(self, predicted_time: float, confidence: float) -> Dict:
        """Calculate min/max time range based on confidence"""
        # Lower confidence = wider range
        range_factor = 1 - confidence
        
        min_time = predicted_time * (1 - range_factor * 0.3)
        max_time = predicted_time * (1 + range_factor * 0.5)
        
        return {
            'min': max(1.0, min_time),
            'max': max_time
        }
    
    def train_model(self, training_data: List[Dict]):
        """
        Train the model with historical data
        
        Args:
            training_data: List of dicts with keys:
                - distance_km
                - avg_congestion
                - avg_speed
                - time_factor
                - actual_time_minutes
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        
        # Prepare features and targets
        X = []
        y = []
        
        for data in training_data:
            X.append([
                data['distance_km'],
                data['avg_congestion'],
                data['avg_speed'],
                data['time_factor']
            ])
            y.append(data['actual_time_minutes'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train Random Forest model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"Model trained - Train R²: {train_score:.3f}, Test R²: {test_score:.3f}")
        
        # Save model
        self._save_model()
        
        return {
            'train_score': train_score,
            'test_score': test_score
        }
    
    def _save_model(self):
        """Save trained model to disk"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            print(f"✓ Model saved to {self.model_path}")
        except Exception as e:
            print(f"⚠ Error saving model: {e}")


# Global predictor instance
_predictor_instance = None

def get_predictor() -> TravelTimePredictor:
    """Get singleton predictor instance"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = TravelTimePredictor()
    return _predictor_instance
