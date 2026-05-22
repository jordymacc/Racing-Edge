from plyer import notification
from datetime import datetime
import platform

def send_desktop_notification(title, message, timeout=10):
    """Send desktop notification (works on Windows, Mac, Linux)"""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='JordyMac Racing',
            timeout=timeout
        )
        print(f"📬 Notification sent: {title}")
    except Exception as e:
        print(f"⚠️ Desktop notification failed: {e}")


def send_bet_alert(horse_name, race_name, odds, confidence):
    """Send alert for high-confidence bet"""
    title = f"🔥 HOT BET ALERT!"
    message = (
        f"{horse_name}\n"
        f"{race_name}\n"
        f"${odds} — {confidence:.1f}% confidence"
    )
    
    send_desktop_notification(title, message, timeout=15)


def send_winner_alert(horse_name, race_name, predicted_prob):
    """Alert when a predicted winner actually wins"""
    title = f"🏆 WINNER! Model Correct!"
    message = (
        f"{horse_name} WON!\n"
        f"{race_name}\n"
        f"Predicted: {predicted_prob:.1f}%"
    )
    
    send_desktop_notification(title, message, timeout=20)


def send_daily_summary(wins, total_bets, roi):
    """Daily performance notification"""
    title = f"📊 Daily Summary"
    message = (
        f"Wins: {wins}/{total_bets}\n"
        f"Win Rate: {wins/total_bets*100:.1f}%\n"
        f"ROI: {roi:+.1f}%"
    )
    
    send_desktop_notification(title, message, timeout=10)
