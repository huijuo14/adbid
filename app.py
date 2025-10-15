import requests
from bs4 import BeautifulSoup
import time
import re
import os
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class AdShareTelegramBot:
    def __init__(self):
        self.current_bid = None
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.session = requests.Session()
        self.email = "s.an.t.o.smaic.a36.9@gmail.com"
        self.password = "s.an.t.o.smaic.a36.9@gmail.com"
        
        # Bot state
        self.is_monitoring = False
        self.check_interval = 300  # 5 minutes
        self.custom_alert = None
        self.bid_history = []
        self.session_stats = {
            'start_time': None,
            'checks_made': 0,
            'changes_detected': 0,
            'last_change': None
        }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    def send_telegram(self, message, parse_mode='HTML'):
        """Send message via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id, 
                "text": message, 
                "parse_mode": parse_mode
            }
            response = self.session.post(url, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def process_telegram_command(self, command):
        """Process incoming Telegram commands"""
        try:
            # Get updates from Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    if 'message' in update and 'text' in update['message']:
                        text = update['message']['text']
                        chat_id = update['message']['chat']['id']
                        
                        # Process commands
                        if text.startswith('/'):
                            self.handle_command(text, chat_id)
                            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
    
    def handle_command(self, command, chat_id):
        """Handle specific commands"""
        command = command.lower().strip()
        
        if command == '/start':
            self.start_monitoring()
            self.send_telegram("🚀 <b>Bid Monitor Started!</b>\nMonitoring AdShare bids every 5 minutes.")
            
        elif command == '/stop':
            self.stop_monitoring()
            self.send_telegram("🛑 <b>Bid Monitor Stopped!</b>")
            
        elif command == '/status':
            self.send_status()
            
        elif command.startswith('/alert'):
            try:
                alert_bid = int(command.split()[1])
                self.custom_alert = alert_bid
                self.send_telegram(f"🔔 <b>Alert Set!</b>\nI'll notify you when bid reaches {alert_bid} credits.")
            except:
                self.send_telegram("❌ Usage: /alert 160")
                
        elif command.startswith('/frequency'):
            try:
                minutes = int(command.split()[1])
                if 1 <= minutes <= 60:
                    self.check_interval = minutes * 60
                    self.send_telegram(f"⏰ <b>Check Frequency Updated!</b>\nNow checking every {minutes} minutes.")
                else:
                    self.send_telegram("❌ Frequency must be between 1-60 minutes.")
            except:
                self.send_telegram("❌ Usage: /frequency 10")
                
        elif command == '/history':
            self.send_history()
            
        elif command == '/help':
            self.send_help()
            
        else:
            self.send_telegram("❌ Unknown command. Use /help for available commands.")
    
    def send_status(self):
        """Send current status"""
        status_msg = f"""
📊 <b>AdShare Bid Monitor Status</b>

🎯 <b>Current Bid:</b> {self.current_bid or 'Unknown'} credits
🔔 <b>Custom Alert:</b> {self.custom_alert or 'Not set'}
⏰ <b>Check Frequency:</b> {self.check_interval // 60} minutes
🔄 <b>Monitoring:</b> {'✅ Active' if self.is_monitoring else '❌ Inactive'}

<b>Session Stats:</b>
📈 Checks Made: {self.session_stats['checks_made']}
🔄 Changes Detected: {self.session_stats['changes_detected']}
⏱️ Last Change: {self.session_stats['last_change'] or 'Never'}
        """
        self.send_telegram(status_msg)
    
    def send_history(self):
        """Send bid change history"""
        if not self.bid_history:
            self.send_telegram("📝 <b>No bid history yet.</b>")
            return
            
        history_msg = "📈 <b>Bid Change History</b>\n\n"
        for change in self.bid_history[-10:]:  # Last 10 changes
            history_msg += f"🕒 {change['time']}\n"
            history_msg += f"📊 {change['old_bid']} → {change['new_bid']} credits\n"
            history_msg += f"📈 Change: {change['change']:+d} credits\n\n"
            
        self.send_telegram(history_msg)
    
    def send_help(self):
        """Send help message"""
        help_msg = """
🤖 <b>AdShare Bid Bot Commands</b>

/start - Start monitoring bids
/stop - Stop monitoring
/status - Current status & stats
/alert 160 - Set custom bid alert
/frequency 10 - Set check frequency (minutes)
/history - View bid change history
/help - Show this help message

<b>Examples:</b>
• Set alert at 160 credits: <code>/alert 160</code>
• Check every 10 minutes: <code>/frequency 10</code>
• View recent changes: <code>/history</code>
        """
        self.send_telegram(help_msg)
    
    def login_to_adshare(self):
    """Login to AdShare"""
    try:
        login_url = "https://adsha.re/login"
        response = self.session.get(login_url, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        form = soup.find('form', {'name': 'login'})
        if not form:
            logger.error("Login form not found")
            return False
            
        # Get the action URL properly
        action_path = form.get('action', '')
        
        # Build correct URL
        if action_path.startswith('http'):
            post_url = action_path
        else:
            post_url = f"https://adsha.re{action_path}"
        
        logger.info(f"Posting to: {post_url}")
        
        login_data = {
            'mail': self.email,
            '04ce63a75551c350478884bcd8e6530f': self.password
        }
        
        response = self.session.post(post_url, data=login_data, allow_redirects=True)
        
        # Verify login by accessing protected page
        test_response = self.session.get("https://adsha.re/adverts/create", timeout=30)
        return "adverts/create" in test_response.url
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False
    
    def get_top_bid(self):
        """Get current top bid"""
        try:
            url = "https://adsha.re/adverts/create"
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup.find_all(string=re.compile(r'top bid is \d+ credits')):
                match = re.search(r'top bid is (\d+) credits', element)
                if match: 
                    return int(match.group(1))
            return None
            
        except Exception as e:
            logger.error(f"Bid fetch error: {e}")
            return None
    
    def start_monitoring(self):
        """Start monitoring"""
        self.is_monitoring = True
        self.session_stats = {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'checks_made': 0,
            'changes_detected': 0,
            'last_change': None
        }
        logger.info("🚀 Monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
    
    def check_for_bid_change(self):
        """Check for bid changes and send alerts"""
        if not self.is_monitoring:
            return
            
        self.session_stats['checks_made'] += 1
        
        new_bid = self.get_top_bid()
        
        if new_bid:
            # Check for bid change
            if self.current_bid and new_bid != self.current_bid:
                self.session_stats['changes_detected'] += 1
                self.session_stats['last_change'] = datetime.now().strftime('%H:%M:%S')
                
                # Record history
                self.bid_history.append({
                    'time': datetime.now().strftime('%m/%d %H:%M'),
                    'old_bid': self.current_bid,
                    'new_bid': new_bid,
                    'change': new_bid - self.current_bid
                })
                
                # Keep only last 50 records
                if len(self.bid_history) > 50:
                    self.bid_history.pop(0)
                
                # Send change alert
                change_msg = f"""
🚨 <b>BID CHANGED!</b>

📊 Before: {self.current_bid} credits
📊 After: {new_bid} credits  
📈 Change: {new_bid - self.current_bid:}+ credits
🕒 Time: {datetime.now().strftime('%H:%M:%S')}

🔗 <a href="https://adsha.re/adverts/create">View on AdShare</a>
                """
                self.send_telegram(change_msg)
                self.current_bid = new_bid
            
            # Check custom alert
            elif self.custom_alert and new_bid >= self.custom_alert:
                alert_msg = f"""
🔔 <b>CUSTOM ALERT TRIGGERED!</b>

🎯 Target: {self.custom_alert} credits
📊 Current: {new_bid} credits
🕒 Time: {datetime.now().strftime('%H:%M:%S')}

Bid has reached your alert threshold!
                """
                self.send_telegram(alert_msg)
                self.custom_alert = None  # Reset alert
            
            elif not self.current_bid:
                # First check
                self.current_bid = new_bid
                self.send_telegram(f"🎯 <b>Monitoring Started!</b>\nCurrent bid: {new_bid} credits")
            
            else:
                # No change
                logger.info(f"✅ No change: {new_bid} credits")
    
    def run(self):
        """Main bot loop"""
        logger.info("🤖 Starting AdShare Telegram Bot...")
        
        # Initial login
        if not self.login_to_adshare():
            logger.error("❌ Initial login failed")
            return
        
        # Send startup message
        self.send_telegram("🤖 <b>AdShare Bid Bot Started!</b>\nUse /help for commands.")
        
        check_count = 0
        while True:
            try:
                # Process Telegram commands every minute
                if check_count % 1 == 0:  # Every 1 minute
                    self.process_telegram_command(None)
                
                # Check bid every interval
                if check_count % (self.check_interval // 60) == 0:
                    self.check_for_bid_change()
                
                check_count += 1
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                time.sleep(30)

# Start the bot
if __name__ == "__main__":
    bot = AdShareTelegramBot()
    bot.run()
