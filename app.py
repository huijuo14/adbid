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

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
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
        self.github_token = os.environ.get('GITHUB_TOKEN')
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
        self.current_global_bid = 0
        self.sent_alerts = {}
        self.gist_id = None  # Store Gist ID for updates
        
        # Timing
        self.check_interval = 300  # 5 minutes
        self.bid_cooldown = 60
        
        # Load saved data
        if self.github_token:
            self.load_from_github()
        else:
            logger.warning("GitHub token not set - data persistence disabled")
        
        logger.info("Smart Bidder initialized with Gist persistence")

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
            logger.warning("GIST_SAVE: No token - skipping save")
            return False
            
        try:
            data = {
                'bid_history': self.bid_history,
                'campaigns': self.campaigns,
                'max_bid_limit': self.max_bid_limit,
                'auto_bid_enabled': self.auto_bid_enabled,
                'current_global_bid': self.current_global_bid,
                'last_save': datetime.now().isoformat(),
                'gist_id': self.gist_id
            }
            
            # Convert datetime objects to strings
            for item in data['bid_history']:
                if 'time' in item and isinstance(item['time'], datetime):
                    item['time'] = item['time'].isoformat()
            
            # Convert campaign datetime objects
            for campaign in data['campaigns'].values():
                if 'last_checked' in campaign and isinstance(campaign['last_checked'], datetime):
                    campaign['last_checked'] = campaign['last_checked'].isoformat()
            
            gist_data = {
                "description": f"BidBot Data - Last update: {datetime.now().isoformat()}",
                "public": False,
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
            
            # If we have a Gist ID, update existing gist, else create new
            if self.gist_id:
                logger.info(f"GIST_SAVE: Updating existing gist {self.gist_id}")
                url = f"https://api.github.com/gists/{self.gist_id}"
                response = self.session.patch(url, json=gist_data, headers=headers, timeout=30)
            else:
                logger.info("GIST_SAVE: Creating new gist")
                response = self.session.post(url, json=gist_data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                self.gist_id = response_data.get('id')
                logger.info(f"GIST_SAVE: Success - Gist ID: {self.gist_id}")
                self.last_save_time = time.time()
                return True
            else:
                logger.error(f"GIST_SAVE: Failed - {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"GIST_SAVE: Error - {e}")
            return False

    def load_from_github(self):
        """Load data from GitHub Gist"""
        if not self.github_token:
            logger.warning("GIST_LOAD: No token - skipping load")
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.github_token}",
                "Content-Type": "application/json"
            }
            
            # First, get list of all gists to find our bidbot gist
            url = "https://api.github.com/gists"
            logger.info("GIST_LOAD: Searching for existing gists...")
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                gists = response.json()
                bidbot_gist = None
                
                # Find gist with our data file
                for gist in gists:
                    if 'bidbot_data.json' in gist.get('files', {}):
                        bidbot_gist = gist
                        self.gist_id = gist['id']
                        logger.info(f"GIST_LOAD: Found existing gist: {self.gist_id}")
                        break
                
                if bidbot_gist:
                    # Get the gist content
                    gist_url = bidbot_gist['files']['bidbot_data.json']['raw_url']
                    data_response = self.session.get(gist_url, timeout=30)
                    
                    if data_response.status_code == 200:
                        data = json.loads(data_response.text)
                        logger.info("GIST_LOAD: Data fetched, restoring...")
                        
                        # Restore bid history
                        if 'bid_history' in data:
                            restored_count = 0
                            for item in data['bid_history']:
                                if 'time' in item and isinstance(item['time'], str):
                                    try:
                                        item['time'] = datetime.fromisoformat(item['time'])
                                        restored_count += 1
                                    except:
                                        item['time'] = self.get_ist_time()
                            self.bid_history = data['bid_history']
                            logger.info(f"GIST_LOAD: Restored {restored_count} bid history records")
                        
                        # Restore campaigns with merging
                        if 'campaigns' in data:
                            restored_campaigns = 0
                            for campaign_name, campaign_data in data['campaigns'].items():
                                if 'last_checked' in campaign_data and isinstance(campaign_data['last_checked'], str):
                                    try:
                                        campaign_data['last_checked'] = datetime.fromisoformat(campaign_data['last_checked'])
                                    except:
                                        campaign_data['last_checked'] = self.get_ist_time()
                                self.campaigns[campaign_name] = campaign_data
                                restored_campaigns += 1
                            logger.info(f"GIST_LOAD: Restored {restored_campaigns} campaigns")
                        
                        # Restore settings
                        if 'max_bid_limit' in data:
                            self.max_bid_limit = data['max_bid_limit']
                            logger.info(f"GIST_LOAD: Restored max bid limit: {self.max_bid_limit}")
                        
                        if 'auto_bid_enabled' in data:
                            self.auto_bid_enabled = data['auto_bid_enabled']
                            logger.info(f"GIST_LOAD: Restored auto-bid: {self.auto_bid_enabled}")
                        
                        if 'current_global_bid' in data:
                            self.current_global_bid = data['current_global_bid']
                            logger.info(f"GIST_LOAD: Restored global bid: {self.current_global_bid}")
                        
                        # Restore sent alerts to avoid duplicates
                        if 'sent_alerts' in data:
                            self.sent_alerts = data['sent_alerts']
                            logger.info(f"GIST_LOAD: Restored {len(self.sent_alerts)} alert states")
                        
                        logger.info("GIST_LOAD: Data restoration completed")
                        return True
                else:
                    logger.info("GIST_LOAD: No existing bidbot gist found - starting fresh")
                    return False
            else:
                logger.error(f"GIST_LOAD: Failed to fetch gists - {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"GIST_LOAD: Error - {e}")
            return False

    def human_delay(self, min_seconds=1, max_seconds=3):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def force_login(self):
        try:
            logger.info("LOGIN: Attempting login...")
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.error("LOGIN: Login form not found")
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
                logger.error("LOGIN: Password field not found")
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
                logger.info("LOGIN: Successful")
                return True
            
            logger.error("LOGIN: Failed - invalid credentials or session")
            return False
        except Exception as e:
            logger.error(f"LOGIN: Error - {e}")
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
            logger.info("SESSION: Valid session detected")
            return True
        logger.warning("SESSION: Session expired, re-login required")
        return self.force_login()

    def parse_campaigns(self):
        """Parse all campaigns from adverts page"""
        try:
            logger.info("PARSING: Fetching adverts page...")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            campaigns = {}
            
            # Find ALL campaign divs (both active and completed)
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*'))
            
            logger.info(f"PARSING: Found {len(campaign_divs)} campaign divs")
            
            for i, div in enumerate(campaign_divs):
                try:
                    # Extract campaign name - get first text content
                    campaign_name = ""
                    for element in div.contents:
                        if isinstance(element, str) and element.strip():
                            campaign_name = element.strip()
                            break
                        elif element.name == 'br':
                            break
                    
                    # Clean up campaign name
                    if 'http' in campaign_name:
                        campaign_name = campaign_name.split('http')[0].strip()
                    campaign_name = campaign_name.rstrip('.:- ')
                    
                    if not campaign_name:
                        logger.warning(f"PARSING: Div {i} - No campaign name found")
                        continue
                    
                    text_content = div.get_text()
                    
                    # Extract your bid
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    your_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    # Extract progress
                    progress_match = re.search(r'(\d+,?\d*)\s*/\s*(\d+,?\d*)\s*visitors', text_content.replace(',', ''))
                    if progress_match:
                        current_views = int(progress_match.group(1).replace(',', ''))
                        total_views = int(progress_match.group(2).replace(',', ''))
                    else:
                        current_views = 0
                        total_views = 0
                    
                    # Check status
                    completed = "COMPLETE" in text_content
                    active = "ACTIVE" in text_content
                    
                    # Get auto-bid setting from saved data
                    auto_bid = self.campaigns.get(campaign_name, {}).get('auto_bid', False)
                    
                    campaigns[campaign_name] = {
                        'your_bid': your_bid,
                        'top_bid': self.current_global_bid,  # Use global top bid
                        'auto_bid': auto_bid,
                        'progress': f"{current_views:,}/{total_views:,}",
                        'completion_pct': (current_views / total_views * 100) if total_views > 0 else 0,
                        'completed': completed,
                        'active': active,
                        'status': 'COMPLETED' if completed else 'ACTIVE' if active else 'UNKNOWN',
                        'last_checked': self.get_ist_time()
                    }
                    
                    logger.info(f"PARSING: '{campaign_name}' - Bid: {your_bid} - Progress: {current_views}/{total_views} - Status: {campaigns[campaign_name]['status']}")
                    
                except Exception as e:
                    logger.error(f"PARSING: Error parsing div {i} - {e}")
                    continue
            
            logger.info(f"PARSING: Successfully parsed {len(campaigns)} campaigns")
            return campaigns
            
        except Exception as e:
            logger.error(f"PARSING: Error - {e}")
            return {}

    def get_global_top_bid(self):
        """Get the global top bid from any campaign"""
        try:
            logger.info("BID_CHECK: Getting global top bid...")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            assign_links = soup.find_all('a', href=re.compile(r'/adverts/assign/'))
            
            if not assign_links:
                logger.warning("BID_CHECK: No assign links found")
                return 0
            
            # Use first campaign to check global top bid
            first_link = assign_links[0]['href']
            if not first_link.startswith('http'):
                first_link = f"https://adsha.re{first_link}"
            
            logger.info(f"BID_CHECK: Checking bid page: {first_link}")
            response = self.session.get(first_link, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            top_bid_match = re.search(r'top bid is (\d+) credits', page_text)
            if top_bid_match:
                top_bid = int(top_bid_match.group(1))
                logger.info(f"BID_CHECK: Global top bid = {top_bid} credits")
                return top_bid
            
            logger.warning("BID_CHECK: No top bid found in page")
            return 0
        except Exception as e:
            logger.error(f"BID_CHECK: Error - {e}")
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
            logger.error(f"CREDITS: Visitor credits error - {e}")
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
            logger.error(f"CREDITS: Traffic credits error - {e}")
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
            logger.error(f"TELEGRAM: Send error - {e}")
            return False

    def check_bid_drop(self, new_bid):
        """Check if global bid dropped significantly"""
        if len(self.bid_history) < 2:
            return False, 0
        
        previous_bid = self.bid_history[-1]['bid']
        
        # Alert if bid drops by more than 50 credits
        if new_bid < previous_bid - 50:
            drop_amount = previous_bid - new_bid
            logger.info(f"BID_ALERT: Drop detected {previous_bid} → {new_bid} (-{drop_amount})")
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
            logger.error(f"TELEGRAM: Command error - {e}")

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
        logger.info("MONITORING: Started")
        self.send_telegram("🚀 SMART BIDDER ACTIVATED!\n\n24/7 monitoring with Gist persistence!")

    def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("MONITORING: Stopped")
        self.send_telegram("🛑 Monitoring STOPPED")

    def send_enhanced_status(self):
        """Enhanced status with global bid tracking"""
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
            
        status_msg = f"""
📊 ENHANCED STATUS REPORT

💰 CREDITS:
Traffic: {traffic_credits} | Visitors: {visitor_credits:,}

🎯 GLOBAL TOP BID: {self.current_global_bid} credits

🏆 CAMPAIGN STATUS:
"""
        
        if self.campaigns:
            for name, data in self.campaigns.items():
                is_top = data.get('your_bid', 0) >= data.get('top_bid', 0)
                status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
                position = "🏆 #1" if is_top else "📉 #2+"
                
                # Add completion status
                status_icon = "✅" if data.get('completed') else "🟢" if data.get('active') else "⚪"
                
                status_msg += f"{position} {status_icon} {name}\n"
                status_msg += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {status}\n"
                status_msg += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n\n"
        else:
            status_msg += "No campaigns detected yet. Checking adverts page...\n\n"

        status_msg += f"🕒 {current_time} IST | 🤖 Bot is actively monitoring..."
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        """Detailed campaign list"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns found yet. The bot is checking adverts page...")
            return
        
        campaigns_text = "📋 YOUR CAMPAIGNS\n\n"
        
        for name, data in self.campaigns.items():
            auto_status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
            position = "🏆 #1" if data.get('your_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
            status_icon = "✅ COMPLETED" if data.get('completed') else "🟢 ACTIVE" if data.get('active') else "⚪ UNKNOWN"
            
            campaigns_text += f"{position} <b>{name}</b>\n"
            campaigns_text += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {auto_status}\n"
            campaigns_text += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
            campaigns_text += f"   📊 Status: {status_icon}\n\n"
        
        campaigns_text += "💡 Use /auto [campaign] on/off to control auto-bidding"
        self.send_telegram(campaigns_text)

    def send_bid_history(self):
        """Enhanced bid history with global bids"""
        if not self.bid_history:
            self.send_telegram("📊 No bid history yet. Monitoring in progress...")
            return
        
        history_msg = "📈 GLOBAL BID HISTORY (Last 10 changes):\n\n"
        
        for record in self.bid_history[-10:]:
            if 'time' in record and isinstance(record['time'], datetime):
                time_str = self.format_ist_time(record['time'])
            else:
                time_str = "Unknown"
            history_msg += f"🕒 {time_str} - {record['bid']} credits\n"
        
        # Add current bid info
        if self.bid_history:
            current_bid = self.bid_history[-1]['bid']
            if len(self.bid_history) >= 2:
                previous_bid = self.bid_history[-2]['bid']
                change = current_bid - previous_bid
                change_icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                history_msg += f"\n{change_icon} Current: {current_bid} credits (Change: {change:+d})"
        
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
/status - Enhanced status with global bids
/campaigns - List all campaigns
/bids - Global bid history
/target [amount] - Set max bid limit
/autobid on/off - Auto-bid for all campaigns
/auto [campaign] on/off - Auto-bid for specific campaign

💡 FEATURES:
• Global top bid tracking
• Campaign progress monitoring  
• Bid drop alerts (50+ credits)
• Auto-bidding for #1 spot
• GitHub Gist persistence
• IST timezone
"""
        self.send_telegram(help_msg)

    def send_hourly_status(self):
        """Automatic hourly status report"""
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

🎯 GLOBAL TOP BID: {self.current_global_bid} credits

"""
        
        if self.campaigns:
            status_msg += "📊 YOUR CAMPAIGNS:\n"
            for name, data in self.campaigns.items():
                if 'progress' in data:
                    position = "🏆 #1" if data.get('your_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
                    status_icon = "✅" if data.get('completed') else "🟢"
                    status_msg += f"{position} {status_icon} \"{name}\" - {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
        
        if self.bid_history:
            current_bid = self.bid_history[-1]['bid'] if self.bid_history else 0
            if len(self.bid_history) >= 2:
                previous_bid = self.bid_history[-2]['bid']
                change = current_bid - previous_bid
                change_icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                status_msg += f"\n{change_icon} Bid Change: {previous_bid} → {current_bid} ({change:+d} credits)"
        
        status_msg += "\n\n🤖 Bot is actively monitoring..."
        
        self.send_telegram(status_msg)
        logger.info("HOURLY_STATUS: Sent automatic report")

    def check_and_alert(self):
        """Main monitoring function with global bid tracking"""
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("MONITORING: Cannot check - login failed")
            return
        
        # Get global top bid
        global_top_bid = self.get_global_top_bid()
        
        if global_top_bid > 0:
            # Record bid history
            self.bid_history.append({
                'bid': global_top_bid,
                'time': self.get_ist_time(),
                'type': 'global'
            })
            
            # Keep only last 100 records
            if len(self.bid_history) > 100:
                self.bid_history = self.bid_history[-100:]
            
            # Update global bid
            self.current_global_bid = global_top_bid
            
            # Check for bid drops
            if len(self.bid_history) >= 2:
                drop_detected, drop_amount = self.check_bid_drop(global_top_bid)
                if drop_detected:
                    current_time = time.time()
                    if current_time - self.last_alert_time > 3600:  # 1 hour cooldown
                        previous_bid = self.bid_history[-2]['bid']
                        alert_msg = f"""
📉 BID DROP OPPORTUNITY!

Global top bid dropped from {previous_bid} → {global_top_bid} credits
💰 SAVE {drop_amount} CREDITS!

Perfect time to start new campaign!
"""
                        self.send_telegram(alert_msg)
                        self.last_alert_time = current_time
                        logger.info(f"BID_ALERT: Sent drop alert - saved {drop_amount} credits")
        
        # Parse campaigns with updated global bid
        new_campaigns = self.parse_campaigns()
        
        # Update campaigns with global top bid
        for campaign_name in new_campaigns:
            new_campaigns[campaign_name]['top_bid'] = self.current_global_bid
        
        self.campaigns = new_campaigns
        
        # Check for campaign completion alerts
        for campaign_name, campaign_data in self.campaigns.items():
            if campaign_data.get('completed') and campaign_data.get('completion_pct', 0) >= 99.9:
                alert_key = f"completed_{campaign_name}"
                if alert_key not in self.sent_alerts:
                    self.send_telegram(f"✅ Campaign Completed:\n\"{campaign_name}\" - {campaign_data['progress']} (100%)\n🚨 EXTEND NOW - Bid reset to 0!")
                    self.sent_alerts[alert_key] = True
                    logger.info(f"CAMPAIGN_ALERT: Sent completion alert for {campaign_name}")
        
        # Auto-save to GitHub Gist every hour
        if time.time() - self.last_save_time > 3600:
            self.save_to_github()

    def run(self):
        logger.info("🚀 Starting Smart Bidder with Gist persistence...")
        
        if not self.force_login():
            logger.error("❌ Failed to start - login failed")
            return
        
        # Initialize sent alerts if not loaded
        if not hasattr(self, 'sent_alerts'):
            self.sent_alerts = {}
        
        persistence_status = "with GitHub Gist persistence" if self.github_token else "without persistence"
        startup_msg = f"🤖 SMART BIDDER STARTED!\n• {persistence_status}\n• Global bid tracking\n• Enhanced logging\n• IST timezone\nType /help for commands"
        self.send_telegram(startup_msg)
        
        last_check = 0
        last_command_check = 0
        last_hourly_status = time.time()
        
        logger.info("🔄 Entering main monitoring loop...")
        
        while True:
            try:
                current_time = time.time()
                
                # Process commands every 3 seconds
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Check bids every 5 minutes if monitoring
                if self.is_monitoring and current_time - last_check >= self.check_interval:
                    logger.info("🔍 Performing scheduled bid check...")
                    self.check_and_alert()
                    last_check = current_time
                    logger.info("✅ Bid check completed")
                
                # Hourly status report
                if self.is_monitoring and current_time - last_hourly_status >= 3600:
                    logger.info("🕐 Sending hourly status report...")
                    self.send_hourly_status()
                    last_hourly_status = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = SmartBidder()
    bot.run()