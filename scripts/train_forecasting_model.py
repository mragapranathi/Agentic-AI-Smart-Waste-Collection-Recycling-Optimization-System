#!/usr/bin/env python
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.training.train import train_forecasting_pipeline

if __name__ == "__main__":
    print("=== Training Waste Generation ML Models ===")
    train_forecasting_pipeline()
    print("=== Training Complete ===")
