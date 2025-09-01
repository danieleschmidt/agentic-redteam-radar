"""
Machine Learning Engine with Real Implementation
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
from datetime import datetime
import pickle
import hashlib

@dataclass
class Model:
    """ML Model wrapper"""
    id: str
    name: str
    version: str
    created_at: datetime
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    model_data: Any = None

class MLEngine:
    """
    Real ML engine implementation with actual algorithms
    """
    
    def __init__(self):
        self.models = {}
        self.training_history = []
        
    def train_model(self, X: np.ndarray, y: np.ndarray, 
                   model_type: str = "linear") -> Model:
        """Train a real model"""
        
        if model_type == "linear":
            model = self._train_linear_regression(X, y)
        elif model_type == "logistic":
            model = self._train_logistic_regression(X, y)
        elif model_type == "cluster":
            model = self._train_clustering(X)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Store model
        self.models[model.id] = model
        self.training_history.append({
            "model_id": model.id,
            "timestamp": datetime.now().isoformat(),
            "type": model_type
        })
        
        return model
    
    def _train_linear_regression(self, X: np.ndarray, y: np.ndarray) -> Model:
        """Simple linear regression implementation"""
        # Add bias term
        X_with_bias = np.c_[np.ones(X.shape[0]), X]
        
        # Normal equation: theta = (X'X)^-1 X'y
        theta = np.linalg.inv(X_with_bias.T @ X_with_bias) @ X_with_bias.T @ y
        
        # Calculate metrics
        predictions = X_with_bias @ theta
        mse = np.mean((predictions - y) ** 2)
        r2 = 1 - (np.sum((y - predictions) ** 2) / np.sum((y - y.mean()) ** 2))
        
        model = Model(
            id=self._generate_model_id(),
            name="LinearRegression",
            version="1.0",
            created_at=datetime.now(),
            parameters={"theta": theta.tolist()},
            metrics={"mse": mse, "r2": r2},
            model_data=theta
        )
        
        return model
    
    def _train_logistic_regression(self, X: np.ndarray, y: np.ndarray, 
                                  iterations: int = 1000, 
                                  learning_rate: float = 0.01) -> Model:
        """Logistic regression with gradient descent"""
        X_with_bias = np.c_[np.ones(X.shape[0]), X]
        theta = np.zeros(X_with_bias.shape[1])
        
        for _ in range(iterations):
            z = X_with_bias @ theta
            predictions = 1 / (1 + np.exp(-z))
            gradient = X_with_bias.T @ (predictions - y) / len(y)
            theta -= learning_rate * gradient
        
        # Calculate accuracy
        final_predictions = (1 / (1 + np.exp(-X_with_bias @ theta))) > 0.5
        accuracy = np.mean(final_predictions == y)
        
        model = Model(
            id=self._generate_model_id(),
            name="LogisticRegression",
            version="1.0",
            created_at=datetime.now(),
            parameters={"theta": theta.tolist(), "iterations": iterations},
            metrics={"accuracy": accuracy},
            model_data=theta
        )
        
        return model
    
    def _train_clustering(self, X: np.ndarray, k: int = 3, 
                         iterations: int = 100) -> Model:
        """K-means clustering implementation"""
        n_samples = X.shape[0]
        
        # Initialize centroids randomly
        idx = np.random.choice(n_samples, k, replace=False)
        centroids = X[idx]
        
        for _ in range(iterations):
            # Assign points to nearest centroid
            distances = np.array([
                np.linalg.norm(X - centroid, axis=1) 
                for centroid in centroids
            ])
            labels = np.argmin(distances, axis=0)
            
            # Update centroids
            new_centroids = np.array([
                X[labels == i].mean(axis=0) if np.sum(labels == i) > 0 else centroids[i]
                for i in range(k)
            ])
            
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids
        
        # Calculate inertia
        inertia = sum(np.min([
            np.linalg.norm(X - centroid, axis=1) ** 2 
            for centroid in centroids
        ], axis=0))
        
        model = Model(
            id=self._generate_model_id(),
            name="KMeans",
            version="1.0",
            created_at=datetime.now(),
            parameters={"k": k, "centroids": centroids.tolist()},
            metrics={"inertia": inertia, "n_clusters": k},
            model_data={"centroids": centroids, "labels": labels}
        )
        
        return model
    
    def predict(self, model_id: str, X: np.ndarray) -> np.ndarray:
        """Make predictions with a trained model"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        if model.name == "LinearRegression":
            X_with_bias = np.c_[np.ones(X.shape[0]), X]
            return X_with_bias @ model.model_data
        
        elif model.name == "LogisticRegression":
            X_with_bias = np.c_[np.ones(X.shape[0]), X]
            z = X_with_bias @ model.model_data
            return (1 / (1 + np.exp(-z))) > 0.5
        
        elif model.name == "KMeans":
            centroids = model.model_data["centroids"]
            distances = np.array([
                np.linalg.norm(X - centroid, axis=1) 
                for centroid in centroids
            ])
            return np.argmin(distances, axis=0)
        
        else:
            raise ValueError(f"Unknown model type: {model.name}")
    
    def _generate_model_id(self) -> str:
        """Generate unique model ID"""
        content = f"{datetime.now().isoformat()}_{np.random.rand()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def save_model(self, model_id: str, filepath: str):
        """Save model to disk"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        with open(filepath, 'wb') as f:
            pickle.dump(self.models[model_id], f)
    
    def load_model(self, filepath: str) -> Model:
        """Load model from disk"""
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
        self.models[model.id] = model
        return model

# Example usage
if __name__ == "__main__":
    # Create engine
    engine = MLEngine()
    
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(100, 3)
    y = X @ np.array([1.5, -2.0, 0.5]) + np.random.randn(100) * 0.1
    
    # Train model
    model = engine.train_model(X, y, model_type="linear")
    print(f"Model trained: {model.id}")
    print(f"Metrics: {model.metrics}")
    
    # Make predictions
    X_test = np.random.randn(10, 3)
    predictions = engine.predict(model.id, X_test)
    print(f"Predictions: {predictions[:5]}")
