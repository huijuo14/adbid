import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime
import os
import json
import pytz

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
        self.github_token = os.environ.get('GITHUB_TOKEN')  # NO DEFAULT - USE RAILWAY ENV
        self.last_update_id = 0
        
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        # Monitoring settings
        self.is_monitoring = False
        self.auto_bid_enabled = False
        self.max_bid_limit = 100
        
        # Data storage
        self.bid_history = []
        self.campaigns = {}
        self.last_alert_time = 0
        self.last_save_time = 0
        
        # Timing
        self.check_interval = 300  # 5 minutes
        self.bid_cooldown = 60
        
        # Load saved data
        if self.github_token:
            self.load_from_github()
        else:
            logger.warning("GitHub token not set - data persistence disabled")
        
        logger.info("Smart Bidder initialized")

    def rotate_user_agent(self):
        user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def get_ist_time(self):
        """Get current time in IST"""
        ist = pytz.timezone('Asia/Kolkata')
        return datetime.now(ist)

    def format_ist_time(self, dt=None):
        """Format time in 2:11 PM format"""
        if dt is None:
            dt = self.get_ist_time()
        return dt.strftime("%I:%M %p")

    def save_to_github(self):
        """Save data to GitHub Gist"""
        if not self.github_token:
            logger.warning("GitHub token not set - skipping save")
            return False
            
        try:
            data = {
                'bid_history': self.bid_history,
                'campaigns': self.campaigns,
                'max_bid_limit': self.max_bid_limit,
                'auto_bid_enabled': self.auto_bid_enabled,
                'last_save': datetime.now().isoformat()
            }
            
            # Convert datetime objects to strings
            for item in data['bid_history']:
                if 'time' in item and isinstance(item['time'], datetime):
                    item['time'] = item['time'].isoformat()
            
            gist_data = {
                "files": {
                    "bidbot_data.json": {
                        "content": json.dumps(data, indent=2)
                    }
                }
            }
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Content-Type": "application/json"
            }
            
            url = "https://api.github.com/gists"
            response = self.session.post(url, json=gist_data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info("Data saved to GitHub")
                self.last_save_time = time.time()
                return True
            else:
                logger.error(f"GitHub save failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"GitHub save error: {e}")
            return False

    def load_from_github(self):
        """Load data from GitHub Gist"""
        if not self.github_token:
            logger.warning("GitHub token not set - skipping load")
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.github_token}",
                "Content-Type": "application/json"
            }
            
            url = "https://api.github.com/gists"
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                gists = response.json()
                for gist in gists:
                    if 'bidbot_data.json' in gist['files']:
                        gist_url = gist['files']['bidbot_data.json']['raw_url']
                        data_response = self.session.get(gist_url, timeout=30)
                        
                        if data_response.status_code == 200:
                            data = json.loads(data_response.text)
                            
                            # Restore bid history
                            if 'bid_history' in data:
                                for item in data['bid_history']:
                                    if 'time' in item and isinstance(item['time'], str):
                                        try:
                                            item['time'] = datetime.fromisoformat(item['time'])
                                        except:
                                            item['time'] = self.get_ist_time()
                                self.bid_history = data['bid_history']
                            
                            # Restore campaigns
                            if 'campaigns' in data:
                                self.campaigns = data['campaigns']
                            
                            # Restore settings
                            if 'max_bid_limit' in data:
                                self.max_bid_limit = data['max_bid_limit']
                            if 'auto_bid_enabled' in data:
                                self.auto_bid_enabled = data['auto_bid_enabled']
                            
                            logger.info("Data loaded from GitHub")
                            return True
            
            logger.info("No existing data found on GitHub")
            return False
            
        except Exception as e:
            logger.error(f"GitHub load error: {e}")
            return False

    # ... (REST OF THE METHODS STAY EXACTLY THE SAME AS BEFORE)
    # human_delay, force_login, check_session_valid, smart_login, parse_campaigns, 
    # get_top_bid, get_visitor_credits, get_traffic_credits, send_telegram, 
    # check_bid_drop, process_telegram_command, handle_command, handle_auto_command,
    # start_monitoring, stop_monitoring, send_enhanced_status, send_campaigns_list,
    # send_bid_history, set_max_bid, send_help, send_hourly_status, check_and_alert, run

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

    def parse_campaigns(self):
        """Parse all campaigns from adverts page"""
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            campaigns = {}
            
            # Find campaign divs
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                try:
                    # Extract campaign name (first line before URL)
                    campaign_name = ""
                    for element in div.contents:
                        if isinstance(element, str) and element.strip():
                            campaign_name = element.strip()
                            break
                        elif element.name == 'br':
                            break
                    
                    if 'http' in campaign_name:
                        campaign_name = campaign_name.split('http')[0].strip()
                    campaign_name = campaign_name.rstrip('.:- ')
                    
                    if not campaign_name:
                        continue
                    
                    text_content = div.get_text()
                    
                    # Extract your bid
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    your_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    # Extract progress
                    progress_match = re.search(r'(\d+)\s*/\s*(\d+)\s*visitors', text_content)
                    current_views = int(progress_match.group(1)) if progress_match else 0
                    total_views = int(progress_match.group(2)) if progress_match else 0
                    
                    # Check if completed
                    completed = "COMPLETE" in text_content
                    
                    if campaign_name and your_bid > 0:
                        # Get auto-bid setting from saved data
                        auto_bid = self.campaigns.get(campaign_name, {}).get('auto_bid', False)
                        
                        campaigns[campaign_name] = {
                            'your_bid': your_bid,
                            'top_bid': your_bid,  # Will be updated later
                            'auto_bid': auto_bid,
                            'progress': f"{current_views:,}/{total_views:,}",
                            'completion_pct': (current_views / total_views * 100) if total_views > 0 else 0,
                            'completed': completed,
                            'last_checked': self.get_ist_time()
                        }
                        
                except Exception as e:
                    logger.error(f"Error parsing campaign: {e}")
                    continue
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Parse campaigns error: {e}")
            return {}

    def get_top_bid(self, campaign_name):
        """Get current top bid for a campaign"""
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            assign_links = soup.find_all('a', href=re.compile(r'/adverts/assign/'))
            
            for link in assign_links:
                campaign_div = link.find_parent('div', style=re.compile(r'border.*solid.*#8CC63F'))
                if campaign_div and campaign_name in campaign_div.get_text():
                    bid_url = link['href']
                    if not bid_url.startswith('http'):
                        bid_url = f"https://adsha.re{bid_url}"
                    
                    response = self.session.get(bid_url, timeout=30)
                    self.human_delay()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text()
                    
                    top_bid_match = re.search(r'top bid is (\d+) credits', page_text)
                    if top_bid_match:
                        return int(top_bid_match.group(1))
            
            return 0
        except Exception as e:
            logger.error(f"Get top bid error for {campaign_name}: {e}")
            return 0

    def get_visitor_credits(self):
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

    def get_traffic_credits(self):
        try:
            response = self.session.get("https://adsha.re/exchange/credits/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            credit_div = soup.find('div', style=re.compile(r'font-size:22pt'))
            if credit_div:
                credit_text = credit_div.get_text().strip()
                credit_match = re.search(r'(\d+\.?\d*)', credit_text)
                if credit_match:
                    return float(credit_match.group(1))
            return 0
        except Exception as e:
            logger.error(f"Traffic credits error: {e}")
            return 0

    def send_telegram(self, message):
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
        if len(self.bid_history) < 2:
            return False, 0
        
        previous_bid = self.bid_history[-1]['bid']
        
        if new_bid < previous_bid * 0.5:
            drop_amount = previous_bid - new_bid
            return True, drop_amount
        
        return False, 0

    def process_telegram_command(self):
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
        command_lower = command.lower().strip()
        
        if command_lower == '/start':
            self.start_monitoring()
        elif command_lower == '/stop':
            self.stop_monitoring()
        elif command_lower == '/status':
            self.send_enhanced_status()
        elif command_lower == '/campaigns':
            self.send_campaigns_list()
        elif command_lower == '/bids':
            self.send_bid_history()
        elif command_lower == '/autobid on':
            self.auto_bid_enabled = True
            self.save_to_github()
            self.send_telegram("✅ Auto-bid ENABLED for all campaigns")
        elif command_lower == '/autobid off':
            self.auto_bid_enabled = False
            self.save_to_github()
            self.send_telegram("❌ Auto-bid DISABLED for all campaigns")
        elif command_lower.startswith('/auto '):
            self.handle_auto_command(command)
        elif command_lower.startswith('/target'):
            self.set_max_bid(command)
        elif command_lower == '/help':
            self.send_help()
        else:
            self.send_telegram("❌ Unknown command. Use /help for commands")

    def handle_auto_command(self, command):
        parts = command.split()
        if len(parts) >= 3:
            campaign_name = ' '.join(parts[1:-1])
            action = parts[-1].lower()
            
            if action not in ['on', 'off']:
                self.send_telegram("❌ Usage: /auto [campaign] on/off")
                return
            
            found_campaign = None
            for stored_name in self.campaigns.keys():
                if stored_name.lower() == campaign_name.lower():
                    found_campaign = stored_name
                    break
            
            if found_campaign:
                self.campaigns[found_campaign]['auto_bid'] = (action == 'on')
                self.save_to_github()
                status = "enabled" if action == 'on' else "disabled"
                self.send_telegram(f"🔄 Auto-bid {status} for '{found_campaign}'")
            else:
                self.send_telegram(f"❌ Campaign '{campaign_name}' not found")
        else:
            self.send_telegram("❌ Usage: /auto [campaign] on/off")

    def start_monitoring(self):
        self.is_monitoring = True
        logger.info("Monitoring started")
        self.send_telegram("🚀 SMART BIDDER ACTIVATED!\n\n24/7 monitoring with GitHub persistence!")

    def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("Monitoring stopped")
        self.send_telegram("🛑 Monitoring STOPPED")

    def send_enhanced_status(self):
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
            
        status_msg = f"""
📊 ENHANCED STATUS REPORT

💰 CREDITS:
Traffic: {traffic_credits} | Visitors: {visitor_credits:,}

🏆 CAMPAIGN STATUS:
"""
        
        if self.campaigns:
            for name, data in self.campaigns.items():
                is_top = data.get('your_bid', 0) >= data.get('top_bid', 0)
                status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
                position = "🏆 #1" if is_top else f"📉 #{data.get('position', '2+')}"
                
                progress_info = ""
                if 'progress' in data:
                    progress_info = f"\n   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)"
                
                status_msg += f"{position} {name}\n"
                status_msg += f"   💰 Bid: {data['your_bid']} | Top: {data.get('top_bid', 'N/A')} | {status}{progress_info}\n\n"
        else:
            status_msg += "No active campaigns\n\n"

        status_msg += f"🕒 {current_time} IST | 🤖 Bot is actively monitoring..."
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        if not self.campaigns:
            self.send_telegram("📊 No campaigns found yet. Monitoring in progress...")
            return
        
        campaigns_text = "📋 YOUR CAMPAIGNS\n\n"
        
        for name, data in self.campaigns.items():
            auto_status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
            position = "🏆 #1" if data.get('your_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
            
            campaigns_text += f"{position} <b>{name}</b>\n"
            campaigns_text += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {auto_status}\n"
            
            if 'progress' in data:
                campaigns_text += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
            
            campaigns_text += "\n"
        
        campaigns_text += "💡 Use /auto [campaign] on/off to control auto-bidding"
        self.send_telegram(campaigns_text)

    def send_bid_history(self):
        if not self.bid_history:
            self.send_telegram("📊 No bid history yet. Monitoring in progress...")
            return
        
        history_msg = "📈 BID HISTORY (Last 10 changes):\n\n"
        
        for record in self.bid_history[-10:]:
            if 'time' in record and isinstance(record['time'], datetime):
                time_str = self.format_ist_time(record['time'])
            else:
                time_str = "Unknown"
            history_msg += f"🕒 {time_str} - {record['bid']} credits\n"
        
        self.send_telegram(history_msg)

    def set_max_bid(self, command):
        try:
            parts = command.split()
            if len(parts) == 2:
                new_limit = int(parts[1])
                self.max_bid_limit = new_limit
                self.save_to_github()
                self.send_telegram(f"🎯 Max bid limit set to {new_limit} credits")
            else:
                self.send_telegram("❌ Usage: /target [amount]\nExample: /target 100")
        except:
            self.send_telegram("❌ Invalid amount. Use numbers only.")

    def send_help(self):
        help_msg = """
🤖 SMART BIDDER - COMMANDS:

/start - Start 24/7 monitoring
/stop - Stop monitoring
/status - Enhanced status with campaigns
/campaigns - List all campaigns
/bids - Bid history
/target [amount] - Set max bid limit
/autobid on/off - Auto-bid for all campaigns
/auto [campaign] on/off - Auto-bid for specific campaign

💡 FEATURES:
• 24/7 top bid monitoring
• Campaign progress tracking
• Bid drop alerts
• Auto-bidding for #1 spot
• GitHub data persistence
• IST timezone
"""
        self.send_telegram(help_msg)

    def send_hourly_status(self):
        """Send automatic hourly status report"""
        if not self.campaigns and not self.bid_history:
            return
            
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
        
        status_msg = f"""
🕐 HOURLY STATUS REPORT
🕒 {current_time} IST

💰 CREDITS:
Traffic: {traffic_credits}
Visitors: {visitor_credits:,}

"""
        
        if self.campaigns:
            status_msg += "📊 YOUR CAMPAIGNS:\n"
            for name, data in self.campaigns.items():
                if 'progress' in data:
                    position = "🏆 #1" if data.get('your_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
                    status_msg += f"{position} \"{name}\" - {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
        
        if self.bid_history:
            current_bid = self.bid_history[-1]['bid'] if self.bid_history else 0
            status_msg += f"\n🎯 Current Top Bid: {current_bid} credits"
        
        status_msg += "\n\n🤖 Bot is actively monitoring..."
        
        self.send_telegram(status_msg)
        logger.info("Hourly status sent")

    def check_and_alert(self):
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("Cannot check - login failed")
            return
        
        # Parse campaigns
        new_campaigns = self.parse_campaigns()
        
        # Update top bids for each campaign
        for campaign_name in new_campaigns:
            top_bid = self.get_top_bid(campaign_name)
            if top_bid > 0:
                new_campaigns[campaign_name]['top_bid'] = top_bid
                
                # Record bid history
                self.bid_history.append({
                    'bid': top_bid,
                    'time': self.get_ist_time(),
                    'campaign': campaign_name
                })
                
                # Keep only last 100 records
                if len(self.bid_history) > 100:
                    self.bid_history = self.bid_history[-100:]
        
        # Update campaigns
        self.campaigns = new_campaigns
        
        # Check for bid drops
        if len(self.bid_history) >= 2:
            current_bid = self.bid_history[-1]['bid']
            drop_detected, drop_amount = self.check_bid_drop(current_bid)
            if drop_detected:
                current_time = time.time()
                if current_time - self.last_alert_time > 3600:  # 1 hour cooldown
                    previous_bid = self.bid_history[-2]['bid']
                    alert_msg = f"""
📉 BID DROP OPPORTUNITY!

Top bid dropped from {previous_bid} → {current_bid} credits
💰 SAVE {drop_amount} CREDITS!

Perfect time to start new campaign!
"""
                    self.send_telegram(alert_msg)
                    self.last_alert_time = current_time

        # Auto-save to GitHub every hour
        if time.time() - self.last_save_time > 3600:
            self.save_to_github()

    def run(self):
        logger.info("Starting Smart Bidder with GitHub persistence...")
        
        if not self.force_login():
            logger.error("Failed to start - login failed")
            return
        
        persistence_status = "with GitHub persistence" if self.github_token else "without persistence"
        self.send_telegram(f"🤖 SMART BIDDER STARTED!\n• {persistence_status}\n• IST timezone\n• Campaign tracking\nType /help for commands")
        
        last_check = 0
        last_command_check = 0
        last_hourly_status = time.time()
        
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
                
                # Hourly status report
                if self.is_monitoring and current_time - last_hourly_status >= 3600:
                    self.send_hourly_status()
                    last_hourly_status = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = SmartBidder()
    bot.run()