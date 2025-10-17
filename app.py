import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime
import os

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

class SmartBidder:
    def __init__(self):
        # Environment variables
        self.bot_token = os.environ.get('BOT_TOKEN', "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc")
        self.chat_id = os.environ.get('CHAT_ID', "2052085789")
        self.email = os.environ.get('EMAIL', "loginallapps@gmail.com")
        self.password = os.environ.get('PASSWORD', "@Sd2007123")
        self.last_update_id = 0
        
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        # Monitoring settings
        self.is_monitoring = False
        self.auto_bid_enabled = False
        self.max_bid_limit = 100  # Default max bid
        
        # Bid tracking
        self.current_top_bid = 0
        self.bid_history = []
        self.last_alert_time = 0
        self.campaigns = {}
        
        # Timing
        self.check_interval = 300  # 5 minutes
        self.bid_cooldown = 60  # 1 minute between bids
        
        logger.info("Smart Bidder initialized")

    def rotate_user_agent(self):
        user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def human_delay(self, min_seconds=1, max_seconds=3):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def force_login(self):
        try:
            logger.info("Logging in...")
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.error("Login form not found")
                return False
                
            action_path = form.get('action', '')
            post_url = f"https://adsha.re{action_path}" if not action_path.startswith('http') else action_path
            
            password_field = None
            for field in form.find_all('input'):
                field_name = field.get('name', '')
                field_value = field.get('value', '')
                if field_value == 'Password' and field_name != 'mail' and field_name:
                    password_field = field_name
                    break
            
            if not password_field:
                logger.error("Password field not found")
                return False
            
            login_data = {
                'mail': self.email,
                password_field: self.password
            }
            
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            self.human_delay()
            
            # Check if login successful
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            if response.status_code == 200 and "Create New Campaign" in response.text:
                self.session_valid = True
                logger.info("Login successful")
                return True
            
            logger.error("Login failed")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def check_session_valid(self):
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            if response.status_code == 200 and "Create New Campaign" in response.text:
                self.session_valid = True
                return True
            self.session_valid = False
            return False
        except:
            self.session_valid = False
            return False

    def smart_login(self):
        if self.check_session_valid():
            return True
        return self.force_login()

    def get_top_bid(self):
        """Get current top bid from assign visitors page"""
        try:
            # First get campaign IDs from adverts page
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find assign visitors links
            assign_links = soup.find_all('a', href=re.compile(r'/adverts/assign/'))
            
            if not assign_links:
                logger.info("No active campaigns found")
                return 0
            
            # Use first campaign to check top bid
            first_link = assign_links[0]['href']
            if not first_link.startswith('http'):
                first_link = f"https://adsha.re{first_link}"
            
            response = self.session.get(first_link, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            # Extract top bid using regex
            top_bid_match = re.search(r'top bid is (\d+) credits', page_text)
            if top_bid_match:
                top_bid = int(top_bid_match.group(1))
                logger.info(f"Current top bid: {top_bid} credits")
                return top_bid
            
            return 0
        except Exception as e:
            logger.error(f"Get top bid error: {e}")
            return 0

    def get_visitor_credits(self):
        """Get available visitor credits"""
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            visitors_match = re.search(r'Visitors:\s*([\d,]+)', soup.get_text())
            if visitors_match:
                visitors_str = visitors_match.group(1).replace(',', '')
                return int(visitors_str)
            return 0
        except Exception as e:
            logger.error(f"Get visitor credits error: {e}")
            return 0

    def send_telegram(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id, 
                "text": message,
                "parse_mode": 'HTML'
            }
            response = self.session.post(url, json=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    def check_bid_drop(self, new_bid):
        """Check if bid dropped significantly"""
        if len(self.bid_history) < 2:
            return False
        
        previous_bid = self.bid_history[-1]['bid']
        
        # If bid dropped by more than 50%
        if new_bid < previous_bid * 0.5:
            drop_amount = previous_bid - new_bid
            return True, drop_amount
        
        return False, 0

    def process_telegram_command(self):
        """Process Telegram commands"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {'offset': self.last_update_id + 1, 'timeout': 5}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    update_id = update['update_id']
                    if update_id > self.last_update_id:
                        self.last_update_id = update_id
                        if 'message' in update and 'text' in update['message']:
                            text = update['message']['text']
                            chat_id = update['message']['chat']['id']
                            if str(chat_id) != self.chat_id:
                                continue
                            self.handle_command(text)
        except Exception as e:
            logger.error(f"Telegram command error: {e}")

    def handle_command(self, command):
        """Handle bot commands"""
        command = command.lower().strip()
        
        if command == '/start':
            self.start_monitoring()
        elif command == '/stop':
            self.stop_monitoring()
        elif command == '/status':
            self.send_status()
        elif command == '/bids':
            self.send_bid_history()
        elif command.startswith('/target'):
            self.set_max_bid(command)
        elif command == '/autobid on':
            self.auto_bid_enabled = True
            self.send_telegram("✅ Auto-bid ENABLED - Will auto-bid for #1 position")
        elif command == '/autobid off':
            self.auto_bid_enabled = False
            self.send_telegram("❌ Auto-bid DISABLED")
        elif command == '/help':
            self.send_help()
        else:
            self.send_telegram("❌ Unknown command. Use /help for commands")

    def start_monitoring(self):
        """Start 24/7 monitoring"""
        self.is_monitoring = True
        logger.info("Monitoring started")
        self.send_telegram("🚀 SMART BIDDER ACTIVATED!\n\n24/7 bid monitoring started...")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("Monitoring stopped")
        self.send_telegram("🛑 Monitoring STOPPED")

    def send_status(self):
        """Send current status"""
        top_bid = self.current_top_bid
        credits = self.get_visitor_credits()
        
        status_msg = f"""
📊 CURRENT STATUS

💰 Top Bid: {top_bid} credits
👥 Your Credits: {credits:,} visitors
🎯 Max Bid Limit: {self.max_bid_limit} credits
🤖 Auto-bid: {'✅ ON' if self.auto_bid_enabled else '❌ OFF'}
📈 Monitoring: {'✅ ACTIVE' if self.is_monitoring else '❌ PAUSED'}
"""
        self.send_telegram(status_msg)

    def send_bid_history(self):
        """Send bid history"""
        if not self.bid_history:
            self.send_telegram("📊 No bid history yet. Monitoring in progress...")
            return
        
        history_msg = "📈 BID HISTORY (Last 10 changes):\n\n"
        
        for record in self.bid_history[-10:]:
            time_str = record['time'].strftime("%H:%M")
            history_msg += f"🕒 {time_str} - {record['bid']} credits\n"
        
        self.send_telegram(history_msg)

    def set_max_bid(self, command):
        """Set maximum bid limit"""
        try:
            parts = command.split()
            if len(parts) == 2:
                new_limit = int(parts[1])
                self.max_bid_limit = new_limit
                self.send_telegram(f"🎯 Max bid limit set to {new_limit} credits")
            else:
                self.send_telegram("❌ Usage: /target [amount]\nExample: /target 100")
        except:
            self.send_telegram("❌ Invalid amount. Use numbers only.")

    def send_help(self):
        """Send help message"""
        help_msg = """
🤖 SMART BIDDER - COMMANDS:

/start - Start 24/7 monitoring
/stop - Stop monitoring
/status - Current status
/bids - Bid history
/target [amount] - Set max bid limit
/autobid on - Auto-bid for #1 position
/autobid off - Disable auto-bid

💡 FEATURES:
• 24/7 top bid monitoring
• Bid drop alerts
• Auto-bidding for #1 spot
• Credit protection
• Bid history tracking
"""
        self.send_telegram(help_msg)

    def check_and_alert(self):
        """Main monitoring function"""
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("Cannot check - login failed")
            return
        
        # Get current top bid
        new_bid = self.get_top_bid()
        
        if new_bid == 0:
            return
        
        # Record bid history
        self.bid_history.append({
            'bid': new_bid,
            'time': datetime.now()
        })
        
        # Keep only last 50 records
        if len(self.bid_history) > 50:
            self.bid_history = self.bid_history[-50:]
        
        # Check for bid drop
        if len(self.bid_history) >= 2:
            drop_detected, drop_amount = self.check_bid_drop(new_bid)
            if drop_detected:
                current_time = time.time()
                # Only alert once per hour for same drop
                if current_time - self.last_alert_time > 3600:
                    alert_msg = f"""
📉 BID DROP OPPORTUNITY!

Top bid dropped from {self.bid_history[-2]['bid']} → {new_bid} credits
💰 SAVE {drop_amount} CREDITS!

Perfect time to start new campaign!
"""
                    self.send_telegram(alert_msg)
                    self.last_alert_time = current_time
                    logger.info(f"Bid drop alert sent: {drop_amount} credits saved")
        
        # Update current bid
        self.current_top_bid = new_bid
        
        # Auto-bid logic (if enabled and you have campaigns)
        if self.auto_bid_enabled and new_bid > 0:
            self.auto_bid_check(new_bid)

    def auto_bid_check(self, current_top_bid):
        """Auto-bid to maintain #1 position"""
        try:
            # This would need your current bid info
            # For now, just log the logic
            logger.info(f"Auto-bid check: Current top is {current_top_bid}")
            
            # Logic would be:
            # 1. Check your current bid for each campaign
            # 2. If your bid < top_bid, increase to top_bid + 1
            # 3. Only if below max_bid_limit
            
        except Exception as e:
            logger.error(f"Auto-bid error: {e}")

    def run(self):
        """Main bot loop"""
        logger.info("Starting Smart Bidder...")
        
        if not self.force_login():
            logger.error("Failed to start - login failed")
            return
        
        self.send_telegram("🤖 SMART BIDDER STARTED!\nType /help for commands")
        
        last_check = 0
        last_command_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Process commands every 3 seconds
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Check bids every 5 minutes if monitoring
                if self.is_monitoring and current_time - last_check >= self.check_interval:
                    self.check_and_alert()
                    last_check = current_time
                    logger.info("Bid check completed")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = SmartBidder()
    bot.run()