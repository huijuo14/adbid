import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime, timedelta
from flask import Flask
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Ultimate Smart Bidder - Active"

@app.route('/health')
def health():
    return "✅ Bot Healthy"

class UltimateSmartBidder:
    def __init__(self):
        # === CONFIGURABLE SETTINGS ===
        
        # Telegram credentials
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.last_update_id = 0
        
        # AdShare credentials
        self.email = "loginallapps@gmail.com"
        self.password = "@Sd2007123"
        
        # Bidding strategy
        self.minimal_bid_weights = [1, 1, 1, 2, 2, 2, 2]  # +1/+2 weights
        self.random_hold_range = (60, 420)  # 1-7 minutes
        
        # Frequency settings
        self.frequency_modes = {
            'aggressive': {'min': 120, 'max': 180},    # 2-3 minutes
            'conservative': {'min': 900, 'max': 1200}, # 15-20 minutes
            'current_mode': 'conservative'
        }
        
        # Target settings
        self.top_bidder_tracking = {
            'daily_target_minutes': random.randint(480, 600),  # 8-10 hours
            'current_minutes_today': 0,
            'last_reset_date': datetime.now().date(),
            'current_session_start': None,
            'is_currently_top': False
        }
        
        # Credit safety settings
        self.visitor_alert_threshold = 1000  # Alert when below this
        self.visitor_stop_threshold = 500    # Stop bidding when below this
        
        # === END CONFIGURABLE SETTINGS ===
        
        # Session management
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        # Bot settings
        self.is_monitoring = False
        self.campaigns = {}
        
        # Credit balances
        self.current_traffic_credits = 0
        self.current_visitor_credits = 0
        self.last_credit_alert = None
        
        # Performance analytics
        self.performance_analytics = {
            'bid_attempts': 0,
            'bid_successes': 0,
            'views_when_top': [],
            'views_when_not_top': [],
            'hourly_views': {},
            'peak_hours': [14, 15, 16, 11],  # 2PM, 3PM, 4PM, 11AM IST
            'today_views': 0
        }
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'last_auto_bid': None,
            'credits_saved': 0
        }

    def rotate_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ]
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
        })

    def human_delay(self, min_seconds=2, max_seconds=5):
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def get_traffic_credits(self):
        """Get traffic credits balance from exchange page"""
        try:
            response = self.session.get("https://adsha.re/exchange/credits/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the credit balance in the HTML
            credit_div = soup.find('div', style=re.compile(r'font-size:22pt'))
            if credit_div:
                credit_text = credit_div.get_text().strip()
                # Extract number like "1.5"
                credit_match = re.search(r'(\d+\.?\d*)', credit_text)
                if credit_match:
                    return float(credit_match.group(1))
            return 0
        except Exception as e:
            logger.error(f"Error getting traffic credits: {e}")
            return 0

    def get_visitor_credits(self):
        """Get available visitors from adverts page"""
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find "Visitors: 992" text
            visitors_match = re.search(r'Visitors:\s*(\d+)', soup.get_text())
            if visitors_match:
                return int(visitors_match.group(1))
            return 0
        except Exception as e:
            logger.error(f"Error getting visitor credits: {e}")
            return 0

    def check_credit_safety(self):
        """Check if credits are sufficient for bidding"""
        # Update credit balances
        self.current_traffic_credits = self.get_traffic_credits()
        self.current_visitor_credits = self.get_visitor_credits()
        
        # Check visitor credits for alerts
        if self.current_visitor_credits < self.visitor_stop_threshold:
            if self.last_credit_alert != 'stop':
                self.send_telegram(f"🛑 CRITICAL: Only {self.current_visitor_credits} visitors left! Auto-bid stopped.")
                self.last_credit_alert = 'stop'
            return False
            
        elif self.current_visitor_credits < self.visitor_alert_threshold:
            if self.last_credit_alert != 'alert':
                self.send_telegram(f"⚠️ WARNING: Low visitors - {self.current_visitor_credits} left!")
                self.last_credit_alert = 'alert'
            return True
            
        self.last_credit_alert = None
        return True

    def reset_daily_target_if_needed(self):
        today = datetime.now().date()
        if today != self.top_bidder_tracking['last_reset_date']:
            self.top_bidder_tracking = {
                'daily_target_minutes': random.randint(480, 600),
                'current_minutes_today': 0,
                'last_reset_date': today,
                'current_session_start': None,
                'is_currently_top': False
            }
            logger.info(f"🔄 New daily target: {self.top_bidder_tracking['daily_target_minutes']} minutes")
            self.send_telegram(f"🎯 New Daily Target: {self.top_bidder_tracking['daily_target_minutes']//60}h {self.top_bidder_tracking['daily_target_minutes']%60}m")

    def update_top_bidder_tracking(self, campaign_name, is_top_bidder):
        self.reset_daily_target_if_needed()
        current_time = datetime.now()
        
        if is_top_bidder and not self.top_bidder_tracking['is_currently_top']:
            self.top_bidder_tracking['current_session_start'] = current_time
            self.top_bidder_tracking['is_currently_top'] = True
            logger.info(f"🏆 Started top bidder session for {campaign_name}")
            
        elif not is_top_bidder and self.top_bidder_tracking['is_currently_top']:
            if self.top_bidder_tracking['current_session_start']:
                session_duration = (current_time - self.top_bidder_tracking['current_session_start']).total_seconds() / 60
                self.top_bidder_tracking['current_minutes_today'] += session_duration
                logger.info(f"⏱️ Added {session_duration:.1f} top bidder minutes")
            
            self.top_bidder_tracking['current_session_start'] = None
            self.top_bidder_tracking['is_currently_top'] = False

    def update_performance_analytics(self, campaign_name, is_top_bidder, current_views):
        """Track performance metrics for analytics"""
        current_hour = datetime.now().hour
        
        # Track hourly views
        hour_key = f"{datetime.now().date()}_{current_hour}"
        if hour_key not in self.performance_analytics['hourly_views']:
            self.performance_analytics['hourly_views'][hour_key] = 0
        
        # Update views tracking based on position
        if campaign_name in self.campaigns:
            campaign_data = self.campaigns[campaign_name]
            if 'last_views_count' not in campaign_data:
                campaign_data['last_views_count'] = current_views
                return
            
            views_increase = current_views - campaign_data['last_views_count']
            if views_increase > 0:
                self.performance_analytics['hourly_views'][hour_key] += views_increase
                self.performance_analytics['today_views'] += views_increase
                
                if is_top_bidder:
                    self.performance_analytics['views_when_top'].append(views_increase)
                else:
                    self.performance_analytics['views_when_not_top'].append(views_increase)
            
            campaign_data['last_views_count'] = current_views

    def calculate_smart_frequency(self):
        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        
        if current < target * 0.7:
            self.frequency_modes['current_mode'] = 'aggressive'
        else:
            self.frequency_modes['current_mode'] = 'conservative'
            
        mode = self.frequency_modes['current_mode']
        return random.randint(self.frequency_modes[mode]['min'], self.frequency_modes[mode]['max'])

    def calculate_minimal_bid(self, current_top_bid):
        return current_top_bid + random.choice(self.minimal_bid_weights)

    def should_skip_bid_with_random_hold(self, campaign_name):
        campaign_data = self.campaigns.get(campaign_name, {})
        last_bid_time = campaign_data.get('last_bid_time')
        
        if last_bid_time:
            time_since_last_bid = (datetime.now() - last_bid_time).total_seconds()
            random_hold_time = random.randint(*self.random_hold_range)
            
            if time_since_last_bid < random_hold_time:
                if random.random() < 0.3:
                    logger.info(f"⏳ Random hold: {random_hold_time//60}min")
                    return True
        return False

    def smart_login(self):
        if self.check_session_valid():
            self.session_valid = True
            return True
        return self.force_login()

    def check_session_valid(self):
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            if response.status_code == 302 and "login" in response.headers.get('Location', ''):
                self.session_valid = False
                return False
            self.session_valid = True
            return True
        except:
            self.session_valid = False
            return False

    def force_login(self):
        try:
            logger.info("🔄 Logging in...")
            self.human_delay(2, 4)
            
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
                return False
                
            action_path = form.get('action', '')
            post_url = f"https://adsha.re{action_path}" if not action_path.startswith('http') else action_path
            
            login_data = {
                'mail': self.email,
                '04ce63a75551c350478884bcd8e6530f': self.password
            }
            
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            self.human_delay(1, 2)
            
            if self.check_session_valid():
                self.session_valid = True
                self.stats['logins_made'] += 1
                return True
            return False
        except:
            return False

    def send_telegram(self, message, parse_mode='HTML'):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id, 
                "text": message, 
                "parse_mode": parse_mode
            }
            response = self.session.post(url, data=data, timeout=30)
            return response.status_code == 200
        except:
            return False

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
                                
                            if text.startswith('/'):
                                self.handle_command(text, chat_id)
        except:
            pass

    def handle_command(self, command, chat_id):
        command_lower = command.lower().strip()
        
        if command_lower == '/start':
            self.start_monitoring()
        elif command_lower == '/stop':
            self.stop_monitoring()
        elif command_lower == '/status':
            self.send_smart_status()
        elif command_lower.startswith('/auto'):
            self.handle_auto_command(command)
        elif command_lower == '/campaigns':
            self.send_campaigns_list()
        elif command_lower == '/analytics':
            self.send_analytics_report()
        elif command_lower == '/progress':
            self.send_top_bidder_progress()
        elif command_lower == '/help':
            self.send_help()
        else:
            self.send_telegram("❌ Unknown command. Use /help")

    def handle_auto_command(self, command):
        parts = command.split()
        
        if len(parts) == 1:
            self.send_telegram("❌ Usage: /auto [campaign] on/off")
            return
            
        if len(parts) == 2 and parts[1].lower() in ['on', 'off']:
            action = parts[1].lower()
            for campaign_name in self.campaigns:
                self.campaigns[campaign_name]['auto_bid'] = (action == 'on')
            
            status = "enabled" if action == 'on' else "disabled"
            self.send_telegram(f"🔄 Auto-bid {status} for all campaigns")
            return
            
        if len(parts) >= 3:
            campaign_name = ' '.join(parts[1:-1])
            action = parts[-1].lower()
            
            if action not in ['on', 'off']:
                return
            
            found_campaign = None
            for stored_name in self.campaigns.keys():
                if stored_name.lower() == campaign_name.lower():
                    found_campaign = stored_name
                    break
            
            if found_campaign:
                self.campaigns[found_campaign]['auto_bid'] = (action == 'on')
                status = "enabled" if action == 'on' else "disabled"
                self.send_telegram(f"🔄 Auto-bid {status} for '{found_campaign}'")

    def start_monitoring(self):
        self.is_monitoring = True
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("🚀 Smart monitoring started")
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!")

    def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
        self.send_telegram("🛑 Bot Stopped!")

    def send_smart_status(self):
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
        
        # Get fresh credit balances
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
            
        campaigns_list = ""
        top_campaigns = 0
        total_campaigns = len(self.campaigns)
        
        for name, data in self.campaigns.items():
            is_top = data.get('my_bid', 0) >= data.get('top_bid', 0)
            status = "✅" if data.get('auto_bid', False) else "❌"
            position = "🏆 TOP" if is_top else "📉 #2+"
            if is_top:
                top_campaigns += 1
            
            # Add views info
            views_info = ""
            if 'views' in data:
                views = data['views']
                progress_pct = (views['current'] / views['total'] * 100) if views['total'] > 0 else 0
                views_info = f"\n   📊 {views['current']:,}/{views['total']:,} ({progress_pct:.1f}%)"
            
            campaigns_list += f"{position} {name}: {data['my_bid']} credits (Auto: {status}){views_info}\n"

        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        progress_percent = (current / target * 100) if target > 0 else 0

        status_msg = f"""
📊 SMART STATUS

💰 CREDITS BALANCE
Traffic Credits: {traffic_credits}
Available Visitors: {visitor_credits}

⏱️ TOP BIDDER: {current//60}h {current%60}m / {target//60}h {target%60}m ({progress_percent:.1f}%)
🎯 MODE: {self.frequency_modes['current_mode']}
🏆 POSITION: {top_campaigns}/{total_campaigns} at #1

{campaigns_list}
🤖 Auto Bids: {self.stats['auto_bids_made']}
"""
        self.send_telegram(status_msg)

    def send_analytics_report(self):
        # Calculate performance metrics
        bid_success_rate = 0
        if self.performance_analytics['bid_attempts'] > 0:
            bid_success_rate = (self.performance_analytics['bid_successes'] / self.performance_analytics['bid_attempts']) * 100
        
        # Calculate average view rates
        views_when_top = 0
        if self.performance_analytics['views_when_top']:
            views_when_top = sum(self.performance_analytics['views_when_top']) / len(self.performance_analytics['views_when_top'])
        
        views_when_not_top = 0
        if self.performance_analytics['views_when_not_top']:
            views_when_not_top = sum(self.performance_analytics['views_when_not_top']) / len(self.performance_analytics['views_when_not_top'])
        
        analytics_msg = f"""
📈 SMART ANALYTICS

🕐 PEAK HOURS (IST): 2PM, 3PM, 4PM, 11AM
📊 TODAY'S VIEWS: {self.performance_analytics['today_views']}
📈 VIEW RATES:
   • When #1: {views_when_top:.1f}/hour
   • When #2+: {views_when_not_top:.1f}/hour
🎯 BID SUCCESS: {bid_success_rate:.1f}%

💰 CREDITS
Traffic Credits: {self.current_traffic_credits}
Available Visitors: {self.current_visitor_credits}
"""
        self.send_telegram(analytics_msg)

    def send_top_bidder_progress(self):
        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        progress_percent = (current / target * 100) if target > 0 else 0
        
        progress_msg = f"""
⏱️ TOP BIDDER PROGRESS
🎯 Daily Target: {target//60}h {target%60}m
📊 Current: {current//60}h {current%60}m ({progress_percent:.1f}%)
⏳ Remaining: {(target - current)//60}h {((target - current)%60):.0f}m
"""
        self.send_telegram(progress_msg)

    def send_campaigns_list(self):
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
            
        campaigns_msg = "📊 Your Campaigns:\n\n"
        for name, data in self.campaigns.items():
            auto_status = "✅ ON" if data.get('auto_bid', False) else "❌ OFF"
            position = "🏆" if data.get('my_bid', 0) >= data.get('top_bid', 0) else "📉"
            campaigns_msg += f"{position} <b>{name}</b>\n"
            campaigns_msg += f"Bid: {data['my_bid']} credits | Auto: {auto_status}\n"
            
            if 'views' in data:
                views = data['views']
                progress_pct = (views['current'] / views['total'] * 100) if views['total'] > 0 else 0
                campaigns_msg += f"Views: {views['current']:,}/{views['total']:,} ({progress_pct:.1f}%)\n"
            
            campaigns_msg += f"<code>/auto \"{name}\" on</code>\n\n"
        
        self.send_telegram(campaigns_msg)

    def send_help(self):
        help_msg = """
🤖 ULTIMATE SMART BIDDER

/start - Start smart monitoring
/stop - Stop monitoring  
/status - Credits, bids & progress
/campaigns - List campaigns
/analytics - Performance analytics
/progress - Top bidder progress

/auto "My Advert" on - Enable auto-bid
/auto all on - Enable all

💡 FEATURES:
• Smart credit monitoring & safety
• Peak hour optimization (IST)
• Performance analytics
• Minimal +1/+2 bidding
• Auto top bidder tracking
"""
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            new_campaigns = {}
            
            # Exact selector from HTML
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                # Extract clean campaign name
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
                    continue
                
                text_content = div.get_text()
                
                # Extract bid from "Campaign Bid: 151"
                bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                my_bid = int(bid_match.group(1)) if bid_match else 0
                
                # Extract views and hits
                views_match = re.search(r'(\d+)\s*/\s*(\d+)\s*visitors', text_content)
                hits_match = re.search(r'(\d+)\s*hits', text_content)
                
                current_views = int(views_match.group(1)) if views_match else 0
                total_views = int(views_match.group(2)) if views_match else 0
                total_hits = int(hits_match.group(1)) if hits_match else 0
                
                if campaign_name and my_bid > 0:
                    # Preserve auto_bid setting
                    auto_bid = False
                    if campaign_name in self.campaigns:
                        auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                    
                    new_campaigns[campaign_name] = {
                        'my_bid': my_bid,
                        'top_bid': my_bid,  # Will be updated from bid page
                        'auto_bid': auto_bid,
                        'last_bid_time': None,
                        'last_checked': None,
                        'last_views_count': current_views,
                        'views': {
                            'current': current_views,
                            'total': total_views,
                            'hits': total_hits
                        }
                    }
            
            return new_campaigns
        except Exception as e:
            logger.error(f"Error parsing campaigns: {e}")
            return {}

    def get_top_bid_from_bid_page(self, campaign_name):
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            increase_links = soup.find_all('a', href=re.compile(r'/adverts/bid/'))
            
            for link in increase_links:
                campaign_div = link.find_parent('div', style=re.compile(r'border.*solid.*#8CC63F'))
                if campaign_div and campaign_name in campaign_div.get_text():
                    bid_url = link['href']
                    if not bid_url.startswith('http'):
                        bid_url = f"https://adsha.re{bid_url}"
                    
                    response = self.session.get(bid_url, timeout=30)
                    self.human_delay(1, 2)
                    
                    # Extract top bid from bid page HTML
                    soup = BeautifulSoup(response.content, 'html.parser')
                    top_bid_text = soup.get_text()
                    top_bid_match = re.search(r'top bid is (\d+) credits', top_bid_text)
                    
                    if top_bid_match:
                        return int(top_bid_match.group(1))
            return None
        except:
            return None

    def check_all_campaigns(self):
        if not self.is_monitoring:
            return
            
        self.stats['checks_made'] += 1
        
        if not self.smart_login():
            return
        
        # Check credit safety before proceeding
        if not self.check_credit_safety():
            logger.warning("⛔ Credit safety check failed - skipping bids")
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            # Update campaigns while preserving settings
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    # Preserve auto_bid and update other data
                    auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                    self.campaigns[campaign_name].update(new_data)
                    self.campaigns[campaign_name]['auto_bid'] = auto_bid
                else:
                    self.campaigns[campaign_name] = new_data
            
            if not self.campaigns:
                return
            
            # Check each campaign
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    # Update top bid
                    old_top_bid = campaign_data.get('top_bid', 0)
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now()
                    
                    # Update top bidder tracking
                    is_top_bidder = campaign_data['my_bid'] >= top_bid
                    self.update_top_bidder_tracking(campaign_name, is_top_bidder)
                    
                    # Update performance analytics
                    self.update_performance_analytics(campaign_name, is_top_bidder, campaign_data['views']['current'])
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}, Top: {is_top_bidder}")
                    
                    # Smart auto-bid logic
                    if (campaign_data['auto_bid'] and 
                        not self.should_skip_bid_with_random_hold(campaign_name)):
                        
                        self.execute_smart_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Check error: {e}")

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        try:
            # Track bid attempt
            self.performance_analytics['bid_attempts'] += 1
            
            # Only bid if we're not top bidder
            if campaign_data['my_bid'] >= current_top_bid:
                return
            
            # Calculate minimal bid
            old_bid = campaign_data['my_bid']
            new_bid = self.calculate_minimal_bid(current_top_bid)
            
            # Don't bid if no change or decrease
            if new_bid <= old_bid:
                return
            
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            increase_links = soup.find_all('a', href=re.compile(r'/adverts/bid/'))
            bid_url = None
            
            for link in increase_links:
                campaign_div = link.find_parent('div', style=re.compile(r'border.*solid.*#8CC63F'))
                if campaign_div and campaign_name in campaign_div.get_text():
                    bid_url = link['href']
                    if not bid_url.startswith('http'):
                        bid_url = f"https://adsha.re{bid_url}"
                    break
            
            if not bid_url:
                return
            
            response = self.session.get(bid_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'bid'})
            
            if not form:
                return
            
            action = form.get('action', '')
            if not action.startswith('http'):
                action = f"https://adsha.re{action}"
            
            # Correct form data
            bid_data = {'bid': str(new_bid), 'vis': '0'}
            self.human_delay(2, 4)
            
            response = self.session.post(action, data=bid_data, allow_redirects=True)
            
            if response.status_code == 200:
                # Track successful bid
                self.performance_analytics['bid_successes'] += 1
                
                # Success - update campaign data
                campaign_data['my_bid'] = new_bid
                campaign_data['last_bid_time'] = datetime.now()
                
                self.stats['auto_bids_made'] += 1
                self.stats['credits_saved'] += (3 - (new_bid - old_bid))
                
                logger.info(f"🚀 SMART BID: {campaign_name} {old_bid}→{new_bid}")
                
                success_msg = f"""
🚀 SMART BID SUCCESS!

📊 Campaign: {campaign_name}
🎯 Bid: {old_bid} → {new_bid} credits
📈 Increase: +{new_bid - old_bid} credits
🏆 Position: #1 Achieved!
"""
                self.send_telegram(success_msg)
                
        except Exception as e:
            logger.error(f"Bid error: {e}")

    def run(self):
        logger.info("🤖 Starting Ultimate Smart Bidder...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!")
        
        last_command_check = 0
        last_campaign_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Process commands every 3 seconds
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Smart campaign checking
                if self.is_monitoring:
                    check_interval = self.calculate_smart_frequency()
                    
                    if current_time - last_campaign_check >= check_interval:
                        self.check_all_campaigns()
                        last_campaign_check = current_time
                        
                        logger.info(f"🔄 Check complete. Next in {check_interval//60}min")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

def run_bot():
    bot = UltimateSmartBidder()
    bot.run()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    app.run(host='0.0.0.0', port=10000, debug=False)
