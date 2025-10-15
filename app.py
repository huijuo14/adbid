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
    return "🤖 Ultimate Smart Bidder - Top Time Tracking & Analytics"

@app.route('/health')
def health():
    return "✅ Bot Healthy - Smart Features Active"

class UltimateSmartBidder:
    def __init__(self):
        # Telegram credentials
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.last_update_id = 0
        
        # AdShare credentials
        self.email = "loginallapps@gmail.com"
        self.password = "@Sd2007123"
        
        # Session management
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        self.consecutive_failures = 0
        
        # Bot settings
        self.is_monitoring = False
        self.campaigns = {}
        
        # 🎯 SMART TOP BIDDER TRACKING
        self.top_bidder_tracking = {
            'daily_target_minutes': random.randint(480, 600),  # 8-10 hours random
            'current_minutes_today': 0,
            'last_reset_date': datetime.now().date(),
            'current_session_start': None,
            'is_currently_top': False
        }
        
        # ⚡ FREQUENCY-BASED AGGRESSION
        self.frequency_modes = {
            'aggressive': {'min': 120, 'max': 180},    # 2-3 minutes
            'conservative': {'min': 900, 'max': 1200}, # 15-20 minutes
            'current_mode': 'conservative'
        }
        
        # 📊 SMART VIEWS ANALYTICS
        self.views_analytics = {
            'hourly_views': {},           # {'14': 45, '15': 52}
            'peak_hours': [],
            'last_views_count': {},
            'best_performing_hours': []
        }
        
        # 💰 MINIMAL BIDDING
        self.minimal_bid_weights = [1, 1, 1, 2, 2, 2, 2]  # Mostly +1, sometimes +2
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'last_auto_bid': None,
            'credits_saved': 0
        }
        
        # 🎲 RANDOM HOLD SETTINGS
        self.random_hold_range = (60, 420)  # 1-7 minutes

    def rotate_user_agent(self):
        """Rotate user agents"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ]
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
        })

    def human_delay(self, min_seconds=2, max_seconds=5):
        """Random delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def reset_daily_target_if_needed(self):
        """Reset daily top bidder target if new day"""
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
            self.send_telegram(f"🎯 New Daily Target: {self.top_bidder_tracking['daily_target_minutes']//60}h {self.top_bidder_tracking['daily_target_minutes']%60}m as #1")

    def update_top_bidder_tracking(self, campaign_name, is_top_bidder):
        """Track exact minutes as top bidder"""
        self.reset_daily_target_if_needed()
        
        current_time = datetime.now()
        
        if is_top_bidder and not self.top_bidder_tracking['is_currently_top']:
            # Started being top bidder
            self.top_bidder_tracking['current_session_start'] = current_time
            self.top_bidder_tracking['is_currently_top'] = True
            logger.info(f"🏆 Started top bidder session for {campaign_name}")
            
        elif not is_top_bidder and self.top_bidder_tracking['is_currently_top']:
            # Stopped being top bidder - add minutes
            if self.top_bidder_tracking['current_session_start']:
                session_duration = (current_time - self.top_bidder_tracking['current_session_start']).total_seconds() / 60
                self.top_bidder_tracking['current_minutes_today'] += session_duration
                logger.info(f"⏱️ Added {session_duration:.1f} top bidder minutes")
                
                # Send progress update every 30 minutes
                if int(self.top_bidder_tracking['current_minutes_today']) % 30 == 0:
                    self.send_top_bidder_progress()
            
            self.top_bidder_tracking['current_session_start'] = None
            self.top_bidder_tracking['is_currently_top'] = False

    def send_top_bidder_progress(self):
        """Send top bidder progress update"""
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

    def calculate_smart_frequency(self):
        """Determine check frequency based on top bidder progress"""
        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        
        # If behind target, check more frequently
        if current < target * 0.7:  # Behind 70% of target
            self.frequency_modes['current_mode'] = 'aggressive'
        else:
            self.frequency_modes['current_mode'] = 'conservative'
            
        mode = self.frequency_modes['current_mode']
        return random.randint(self.frequency_modes[mode]['min'], self.frequency_modes[mode]['max'])

    def update_views_analytics(self, campaign_name, current_views):
        """Track views patterns and detect peak hours"""
        current_hour = datetime.now().hour
        current_date = datetime.now().date()
        
        # Initialize hourly tracking
        hour_key = f"{current_date}_{current_hour}"
        if hour_key not in self.views_analytics['hourly_views']:
            self.views_analytics['hourly_views'][hour_key] = 0
        
        # Calculate views this hour
        if campaign_name in self.views_analytics['last_views_count']:
            previous_views = self.views_analytics['last_views_count'][campaign_name]
            views_increase = current_views - previous_views
            if views_increase > 0:
                self.views_analytics['hourly_views'][hour_key] += views_increase
        
        self.views_analytics['last_views_count'][campaign_name] = current_views
        
        # Update peak hours (once we have enough data)
        if len(self.views_analytics['hourly_views']) > 24:
            self.calculate_peak_hours()

    def calculate_peak_hours(self):
        """Calculate best performing hours"""
        hourly_totals = {}
        
        for hour_key, views in self.views_analytics['hourly_views'].items():
            hour = int(hour_key.split('_')[1])
            if hour not in hourly_totals:
                hourly_totals[hour] = []
            hourly_totals[hour].append(views)
        
        # Calculate average views per hour
        hourly_averages = {}
        for hour, views_list in hourly_totals.items():
            hourly_averages[hour] = sum(views_list) / len(views_list)
        
        # Get top 6 hours
        sorted_hours = sorted(hourly_averages.items(), key=lambda x: x[1], reverse=True)
        self.views_analytics['best_performing_hours'] = [hour for hour, avg in sorted_hours[:6]]
        self.views_analytics['peak_hours'] = self.views_analytics['best_performing_hours']
        
        logger.info(f"📊 Peak hours detected: {self.views_analytics['peak_hours']}")

    def get_current_mode_based_on_hour(self):
        """Aggressive during peak hours, conservative otherwise"""
        current_hour = datetime.now().hour
        if current_hour in self.views_analytics['peak_hours']:
            return 'aggressive'
        return 'conservative'

    def calculate_minimal_bid(self, current_top_bid):
        """Always bid +1 or +2 above current top"""
        return current_top_bid + random.choice(self.minimal_bid_weights)

    def should_skip_bid_with_random_hold(self, campaign_name):
        """Random 1-7 minute hold between bids"""
        campaign_data = self.campaigns.get(campaign_name, {})
        last_bid_time = campaign_data.get('last_bid_time')
        
        if last_bid_time:
            time_since_last_bid = (datetime.now() - last_bid_time).total_seconds()
            random_hold_time = random.randint(*self.random_hold_range)
            
            if time_since_last_bid < random_hold_time:
                if random.random() < 0.3:  # 30% chance to skip during hold
                    logger.info(f"⏳ Random hold: {random_hold_time//60}min")
                    return True
        
        return False

    def smart_login(self):
        """Smart login management"""
        if self.check_session_valid():
            self.session_valid = True
            return True
        return self.force_login()

    def check_session_valid(self):
        """Check if session is valid"""
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
        """Perform login"""
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
        """Send Telegram message"""
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
                                
                            if text.startswith('/'):
                                self.handle_command(text, chat_id)
        except:
            pass

    def handle_command(self, command, chat_id):
        """Handle commands"""
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
        """Handle auto-bid commands"""
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
            if command.count('"') >= 2:
                import shlex
                try:
                    parsed = shlex.split(command)
                    if len(parsed) >= 3:
                        campaign_name = parsed[1]
                        action = parsed[2].lower()
                except:
                    campaign_name = ' '.join(parts[1:-1])
                    action = parts[-1].lower()
            else:
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
        """Start monitoring"""
        self.is_monitoring = True
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("🚀 Smart monitoring started")
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!\nTracking top bidder time & analytics!")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
        self.send_telegram("🛑 Bot Stopped!")

    def send_smart_status(self):
        """Send smart status with all features"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
            
        # Campaign status
        campaigns_list = ""
        top_campaigns = 0
        total_campaigns = len(self.campaigns)
        
        for name, data in self.campaigns.items():
            is_top = data.get('my_bid', 0) >= data.get('top_bid', 0)
            status = "✅" if data.get('auto_bid', False) else "❌"
            position = "🏆 TOP" if is_top else "📉 #2+"
            if is_top:
                top_campaigns += 1
            campaigns_list += f"{position} {name}: {data['my_bid']} credits (Auto: {status})\n"

        # Top bidder progress
        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        progress_percent = (current / target * 100) if target > 0 else 0

        # Current mode
        current_hour = datetime.now().hour
        is_peak_hour = current_hour in self.views_analytics['peak_hours']
        mode_note = "⚡ AGGRESSIVE" if is_peak_hour else "💤 CONSERVATIVE"

        status_msg = f"""
📊 SMART STATUS

⏱️ TOP BIDDER: {current//60}h {current%60}m / {target//60}h {target%60}m ({progress_percent:.1f}%)
🎯 MODE: {mode_note} ({self.frequency_modes['current_mode']})
🏆 POSITION: {top_campaigns}/{total_campaigns} at #1

{campaigns_list}
🤖 Auto Bids: {self.stats['auto_bids_made']}
💎 Credits Saved: {self.stats['credits_saved']}
        """
        self.send_telegram(status_msg)

    def send_analytics_report(self):
        """Send detailed analytics report"""
        if not self.views_analytics['peak_hours']:
            self.send_telegram("📊 Collecting analytics data... check back in a few hours")
            return

        peak_hours_str = ", ".join([f"{h}:00" for h in self.views_analytics['peak_hours'][:4]])
        
        analytics_msg = f"""
📈 SMART ANALYTICS

🕐 PEAK HOURS: {peak_hours_str}
⚡ STRATEGY: Aggressive during peak hours
💤 STRATEGY: Conservative during off-hours

📊 TOP BIDDER TODAY:
• Target: {self.top_bidder_tracking['daily_target_minutes']//60}h
• Current: {self.top_bidder_tracking['current_minutes_today']//60}h
• Progress: {(self.top_bidder_tracking['current_minutes_today']/self.top_bidder_tracking['daily_target_minutes']*100):.1f}%

🎯 BIDDING: Always +1/+2 (minimal)
⏰ HOLDS: Random 1-7 minutes
        """
        self.send_telegram(analytics_msg)

    def send_campaigns_list(self):
        """Show campaigns list"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
            
        campaigns_msg = "📊 Your Campaigns:\n\n"
        for name, data in self.campaigns.items():
            auto_status = "✅ ON" if data.get('auto_bid', False) else "❌ OFF"
            position = "🏆" if data.get('my_bid', 0) >= data.get('top_bid', 0) else "📉"
            campaigns_msg += f"{position} <b>{name}</b>\n"
            campaigns_msg += f"Bid: {data['my_bid']} credits | Auto: {auto_status}\n"
            campaigns_msg += f"<code>/auto \"{name}\" on</code>\n\n"
        
        self.send_telegram(campaigns_msg)

    def send_help(self):
        """Send help message"""
        help_msg = """
🤖 ULTIMATE SMART BIDDER

/start - Start smart monitoring
/stop - Stop monitoring  
/status - Smart status with analytics
/campaigns - List campaigns
/analytics - Detailed analytics report
/progress - Top bidder progress

/auto "My Advert" on - Enable auto-bid
/auto all on - Enable all

💡 FEATURES:
• Tracks exact top bidder time
• Daily 8-10h random target
• Smart frequency adjustment
• Peak hour detection
• Minimal bidding (+1/+2 only)
• Random 1-7 minute holds
        """
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        """Parse campaigns data"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            new_campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                text_content = div.get_text().strip()
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if lines:
                    first_line = lines[0]
                    
                    # Extract campaign name
                    if 'http' in first_line:
                        campaign_name = first_line.split('http')[0].strip()
                    elif 'www.' in first_line:
                        campaign_name = first_line.split('www.')[0].strip()
                    else:
                        campaign_name = first_line
                    
                    campaign_name = campaign_name.rstrip('.:- ')
                    
                    # Extract current bid
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    my_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    # Extract views data
                    views_match = re.search(r'(\d+)\s*/\s*(\d+)\s*visitors', text_content)
                    current_views = int(views_match.group(1)) if views_match else 0
                    total_views = int(views_match.group(2)) if views_match else 0
                    
                    if campaign_name and my_bid > 0:
                        # Update views analytics
                        self.update_views_analytics(campaign_name, current_views)
                        
                        # Preserve auto_bid setting
                        auto_bid = False
                        if campaign_name in self.campaigns:
                            auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                        
                        new_campaigns[campaign_name] = {
                            'my_bid': my_bid,
                            'top_bid': my_bid,
                            'auto_bid': auto_bid,
                            'current_views': current_views,
                            'total_views': total_views,
                            'last_bid_time': None,
                            'last_checked': None
                        }
            
            return new_campaigns
        except Exception as e:
            logger.error(f"Error parsing campaigns: {e}")
            return {}

    def get_top_bid_from_bid_page(self, campaign_name):
        """Get top bid from bid page"""
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
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    top_bid_text = soup.find(string=re.compile(r'top bid is \d+ credits'))
                    
                    if top_bid_text:
                        match = re.search(r'top bid is (\d+) credits', top_bid_text)
                        if match:
                            return int(match.group(1))
            return None
        except:
            return None

    def check_all_campaigns(self):
        """Main checking logic with all smart features"""
        if not self.is_monitoring:
            return
            
        self.stats['checks_made'] += 1
        
        if not self.smart_login():
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            # Update campaigns while preserving settings
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    self.campaigns[campaign_name]['my_bid'] = new_data['my_bid']
                    self.campaigns[campaign_name]['top_bid'] = new_data['top_bid']
                    self.campaigns[campaign_name]['current_views'] = new_data['current_views']
                    self.campaigns[campaign_name]['total_views'] = new_data['total_views']
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
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}, Top: {is_top_bidder}")
                    
                    # Smart auto-bid logic
                    if (campaign_data['auto_bid'] and 
                        not self.should_skip_bid_with_random_hold(campaign_name)):
                        
                        self.execute_smart_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Check error: {e}")

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        """Execute smart auto-bid with all features"""
        try:
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
            
            bid_data = {'bid': str(new_bid), 'vis': '0'}
            self.human_delay(2, 4)
            
            response = self.session.post(action, data=bid_data, allow_redirects=True)
            
            if response.status_code == 200:
                # Success - update campaign data
                campaign_data['my_bid'] = new_bid
                campaign_data['last_bid_time'] = datetime.now()
                
                self.stats['auto_bids_made'] += 1
                self.stats['credits_saved'] += (3 - (new_bid - old_bid))  # Track savings
                
                logger.info(f"🚀 SMART BID: {campaign_name} {old_bid}→{new_bid}")
                
                success_msg = f"""
🚀 SMART BID SUCCESS!

📊 Campaign: {campaign_name}
🎯 Bid: {old_bid} → {new_bid} credits
📈 Increase: +{new_bid - old_bid} credits
🏆 Position: #1 Achieved!

💡 Strategy: Minimal bidding
                """
                self.send_telegram(success_msg)
                
        except Exception as e:
            logger.error(f"Bid error: {e}")

    def run(self):
        """Main loop with smart frequency"""
        logger.info("🤖 Starting Ultimate Smart Bidder...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!\nTracking top bidder time & analytics!")
        
        last_command_check = 0
        last_campaign_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Process commands every 3 seconds
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Smart campaign checking with frequency adjustment
                if self.is_monitoring:
                    check_interval = self.calculate_smart_frequency()
                    
                    if current_time - last_campaign_check >= check_interval:
                        self.check_all_campaigns()
                        last_campaign_check = current_time
                        
                        # Log current mode
                        mode = self.frequency_modes['current_mode']
                        logger.info(f"🔄 Check complete. Next in {check_interval//60}min ({mode} mode)")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

def run_bot():
    """Run the bot"""
    bot = UltimateSmartBidder()
    bot.run()

if __name__ == "__main__":
    # Start bot in background
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask for Render
    app.run(host='0.0.0.0', port=10000, debug=False)
