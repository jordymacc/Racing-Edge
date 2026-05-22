# models/staking.py

def calculate_kelly_stake(win_prob, odds, current_bankroll, multiplier=0.25, max_stake_pct=0.05):
    """
    Calculates the recommended bet size using the Kelly Criterion.
    
    Args:
        win_prob (float): Model's predicted probability of winning (0.0 to 1.0)
        odds (float): Current decimal odds (e.g., 3.50)
        current_bankroll (float): Total current bankroll
        multiplier (float): Fractional Kelly multiplier (0.25 = Quarter Kelly)
        max_stake_pct (float): Maximum allowed stake as a % of bankroll (0.05 = 5%)
        
    Returns:
        tuple: (stake_percentage, stake_amount_in_dollars)
    """
    # Edge cases
    if win_prob <= 0 or odds <= 1.0:
        return 0.0, 0.0
    
    b = odds - 1.0       # Net odds (profit per $1 bet)
    p = win_prob         # Probability of winning
    q = 1.0 - p          # Probability of losing
    
    # Standard Kelly formula: (bp - q) / b
    f_star = (b * p - q) / b
    
    # If the edge is negative, we don't bet
    if f_star <= 0:
        return 0.0, 0.0
        
    # Apply the fractional multiplier (to reduce variance/risk)
    stake_pct = f_star * multiplier
    
    # Cap the maximum stake to protect against model overconfidence
    stake_pct = min(stake_pct, max_stake_pct)
    
    stake_amount = current_bankroll * stake_pct
    
    return stake_pct, stake_amount