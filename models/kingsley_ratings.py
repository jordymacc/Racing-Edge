import pandas as pd
import numpy as np
from datetime import datetime

class KingsleyRatings:
    """
    Implements Kingsley's Professional Price Line and supporting metrics.
    Designed to work alongside your existing feature_engine_v3.py
    """
    
    def __init__(self):
        self.class_weights = {
            'MAIDEN': 50, 'BM58': 58, 'BM64': 64, 'BM70': 70, 'BM78': 78,
            'BM88': 88, 'LISTED': 95, 'G3': 105, 'G2': 115, 'G1': 125
        }
    
    def calculate_bullet_price(self, df):
        """Kingsley's Bullet Price - his personal assessment of fair price"""
        df = df.copy()
        
        # Base components
        df['ClassScore'] = df['Class'].astype(str).str.upper().map(self.class_weights).fillna(65)
        
        # Weight adjustment (lighter = better)
        avg_weight = df['Weight'].mean() if 'Weight' in df.columns else 56
        df['WeightAdj'] = 1.0 - ((df['Weight'] - avg_weight) * 0.025)
        
        # Barrier adjustment
        df['BarrierAdj'] = df['Barrier'].apply(
            lambda x: 1.08 if x <= 4 else 0.92 if x >= 12 else 1.0
        )
        
        # Form score from last 5 starts
        if 'Last 5' in df.columns or 'Form' in df.columns:
            form_col = 'Last 5' if 'Last 5' in df.columns else 'Form'
            df['FormScore'] = df[form_col].astype(str).apply(self._parse_form_score)
        else:
            df['FormScore'] = 1.0
        
        # Combine into a single score
        df['BulletScore'] = (
            df['ClassScore'] * 
            df['WeightAdj'] * 
            df['BarrierAdj'] * 
            df['FormScore']
        )
        
        # Convert score to price (higher score = shorter price)
        df['Bullet_Price'] = (220 / df['BulletScore']).round(2).clip(lower=1.5)
        
        # Value detection
        df['Bullet_vs_Market'] = (df['Market Odds'] / df['Bullet_Price']).round(2)
        df['Kingsley_Value'] = df['Bullet_vs_Market'] > 1.25
        
        return df
    
    def _parse_form_score(self, form_str):
        """Convert form like 2-1-3-4-6 into a score"""
        try:
            positions = [int(x) for x in str(form_str).replace('-', '') if x.isdigit()]
            if not positions:
                return 1.0
            score = sum((11 - p) * w for p, w in zip(positions, [4, 3, 2, 1.5, 1])) / 11.5
            return max(0.6, min(2.0, score))
        except:
            return 1.0
    
    def calculate_csw(self, df):
        """Class + Speed + Weight Rating"""
        df = df.copy()
        
        df['ClassScore'] = df['Class'].astype(str).str.upper().map(self.class_weights).fillna(65)
        
        # Speed component
        if all(col in df.columns for col in ['Position', 'Margin']):
            df['SpeedScore'] = 100 - (df['Position'] * 8) - (df['Margin'] * 3)
        else:
            df['SpeedScore'] = 75
        
        # Weight carried penalty
        df['WeightScore'] = 100 - ((df['Weight'] - 54) * 2.2)
        
        df['CSW_Rating'] = (
            df['ClassScore'] * 0.4 +
            df['SpeedScore'] * 0.35 +
            df['WeightScore'] * 0.25
        ).round(1)
        
        df['CSW_Rank'] = df.groupby('Race Name')['CSW_Rating'].rank(ascending=False) if 'Race Name' in df.columns else df['CSW_Rating'].rank(ascending=False)
        return df
    
    def calculate_cam(self, df):
        """Cruising Acceleration Metric"""
        df = df.copy()
        
        # Cruising (ability to settle and travel)
        if 'Map Position' in df.columns:
            df['Cruising'] = df['Map Position'].astype(str).apply(self._score_cruising)
        else:
            df['Cruising'] = 6.0
            
        # Acceleration (last 200m ability)
        if 'Last200' in df.columns or 'Finish Speed' in df.columns:
            accel_col = 'Last200' if 'Last200' in df.columns else 'Finish Speed'
            df['Acceleration'] = pd.to_numeric(df[accel_col], errors='coerce').fillna(5)
        else:
            df['Acceleration'] = 6.0
        
        df['CAM_Rating'] = ((df['Cruising'] * 0.55) + (df['Acceleration'] * 0.45)).round(1)
        return df
    
    def _score_cruising(self, pos):
        pos = str(pos).lower()
        if any(x in pos for x in ['lead', 'leader', 'on-speed', 'box seat']):
            return 9.0
        elif any(x in pos for x in ['handy', 'forward']):
            return 7.5
        elif any(x in pos for x in ['midfield', 'cover']):
            return 6.0
        else:
            return 3.5
    
    def calculate_race_pressure(self, df):
        """Estimate race tempo and assign pressure level"""
        if 'Map Position' not in df.columns:
            df['Race_Pressure'] = "Average"
            return df
            
        speed_map_count = df['Map Position'].value_counts()
        leader_count = sum(1 for v in speed_map_count.keys() 
                          if any(x in str(v).lower() for x in ['lead','leader']))
        
        if leader_count >= 4:
            pressure = "Very Fast"
        elif leader_count >= 3:
            pressure = "Fast"
        elif leader_count <= 1:
            pressure = "Slow"
        else:
            pressure = "Average"
            
        df['Race_Pressure'] = pressure
        return df
    
    def add_kingsley_columns(self, df):
        """Main function - adds all Kingsley metrics to your dataframe"""
        df = df.copy()
        
        df = self.calculate_bullet_price(df)
        df = self.calculate_csw(df)
        df = self.calculate_cam(df)
        df = self.calculate_race_pressure(df)
        
        # Final combined score
        df['Kingsley_Score'] = (
            df['CSW_Rating'] * 0.4 +
            df['CAM_Rating'] * 0.3 +
            (df['Bullet_Price'].max() / df['Bullet_Price']) * 20
        ).round(1)
        
        return df


def add_kingsley_analysis(df):
    """Helper function to easily call from your existing code"""
    engine = KingsleyRatings()
    return engine.add_kingsley_columns(df)
