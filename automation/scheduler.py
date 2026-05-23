import time
import schedule
from datetime import datetime
from pathlib import Path
import sys

# Add project paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'collectors'))
sys.path.insert(0, str(BASE_DIR / 'models'))
sys.path.insert(0, str(BASE_DIR / 'automation'))

from notifier import send_bet_alert, send_winner_alert, send_daily_summary
from performance_tracker import (
    setup_tracking_tables, log_prediction, settle_predictions, 
    get_performance_stats, print_performance_report
)

# Initialize tracking on startup
try:
    setup_tracking_tables()
except:
    pass

def run_odds_scraper():
    """Scrape live odds"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Running odds scraper...")
    try:
        from racingcom_scraper_v3 import scrape_all_races
        scrape_all_races()
    except Exception as e:
        print(f"❌ Odds scraper failed: {e}")

def run_future_races_scraper():
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Scraping future races...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'collectors'))
        from future_races_scraper import setup_table, scrape_future_races
        setup_table()
        scrape_future_races()
    except Exception as e:
        print(f"❌ Future races scraper failed: {e}")

def run_results_scraper():
    """Check for race results"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Checking for results...")
    try:
        from results_scraper import scrape_todays_results
        scrape_todays_results()
        
        # Settle predictions and check for winners
        settled = settle_predictions()
        if settled > 0:
            print(f"   ✅ Settled {settled} predictions")
            
    except Exception as e:
        print(f"❌ Results scraper failed: {e}")

def retrain_model():
    """Retrain ML model"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Retraining ML model...")
    try:
        from train_model import train_model
        train_model()
    except Exception as e:
        print(f"❌ Model training failed: {e}")

def check_high_confidence_bets():
    """Check for high-confidence betting opportunities"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Scanning for opportunities...")
    try:
        from dashboard_predictions import get_ml_predictions_for_dashboard
        
        predictions = get_ml_predictions_for_dashboard()
        
        if predictions is not None:
            # Filter for very high confidence (90%+)
            very_high = predictions[predictions['win_probability'] > 0.90]
            
            for _, bet in very_high.iterrows():
                # Send notification
                send_bet_alert(
                    bet['horse_name'],
                    bet['race_name'],
                    bet['current_odds'],
                    bet['win_probability'] * 100
                )
                
                # Log prediction
                log_prediction(
                    bet['race_name'],
                    bet['horse_name'],
                    bet['win_probability'],
                    bet['current_odds'],
                    bet['confidence']
                )
            
            if len(very_high) > 0:
                print(f"🔥 {len(very_high)} VERY HIGH CONFIDENCE BETS (>90%)!")
            
            # Show all high conf
            high_conf = predictions[predictions['win_probability'] > 0.35]
            if len(high_conf) > 0:
                print(f"   Total high confidence: {len(high_conf)}")
            else:
                print("   ✅ No high-confidence bets right now")
                
    except Exception as e:
        print(f"❌ Bet checker failed: {e}")

def daily_summary():
    """Generate daily performance summary"""
    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Generating daily summary...")
    try:
        print_performance_report()
        
        stats = get_performance_stats()
        if stats:
            send_daily_summary(
                stats['wins'],
                stats['total_bets'],
                stats['roi']
            )
    except Exception as e:
        print(f"❌ Summary failed: {e}")

def run_automation():
    """Main automation loop"""
    print("=" * 60)
    print("🤖 JORDYMAC AUTOMATED RACING ENGINE v2.0")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🆕 NEW FEATURES:")
    print("  📬 Desktop notifications for hot bets")
    print("  📊 Performance tracking with P&L")
    print("\nSchedule:")
    print("  ⚡ Odds scraper:      Every 60 seconds")
    print("  🏆 Results scraper:   Every 10 minutes")
    print("  🔍 Bet alerts:        Every 2 minutes")
    print("  🤖 Model retrain:     Every 6 hours")
    print("  📊 Daily summary:     9:00 PM daily")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    # Schedule jobs
    schedule.every(1).minutes.do(run_odds_scraper)
    schedule.every(10).minutes.do(run_results_scraper)
    schedule.every(2).minutes.do(check_high_confidence_bets)
    schedule.every(6).hours.do(retrain_model)
    schedule.every(6).hours.do(run_future_races_scraper)
    schedule.every().day.at("21:00").do(daily_summary)
    
    # Run immediately
    run_odds_scraper()
    run_future_races_scraper()
    check_high_confidence_bets()
    
    # Main loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Automation stopped by user")
            print_performance_report()
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_automation()
