import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime, timedelta
from flask import Flask
import threading
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

app = Flask(__name__)

class UltimateSmartBidder:
    def __init__(self):
        # Credentials
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.last_update_id = 0
        self.email = "loginallapps@gmail.com"
        self.password = "@Sd2007123"
        
        # Session
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        # Bot state
        self.is_monitoring = False
        self.campaigns = {}
        
        # Bidding strategy
        self.minimal_bid_weights = [1, 1, 1, 2, 2, 2, 2]
        self.random_hold_range = (60, 420)
        
        # Frequency modes
        self.frequency_modes = {
            'aggressive': {'min': 120, 'max': 180},
            'conservative': {'min': 900, 'max': 1200},
            'current_mode': 'conservative'
        }
        
        # Credit safety
        self.visitor_alert_threshold = 1000
        self.visitor_stop_threshold = 500
        self.current_traffic_credits = 0
        self.current_visitor_credits = 0
        self.last_credit_alert = None
        
        # Target tracking
        self.top_bidder_tracking = {
            'daily_target_minutes': random.randint(360, 480),
            'current_minutes_today': 0,
            'last_reset_date': datetime.now().date(),
            'current_session_start': None,
            'is_currently_top': False
        }
        
        # SMART ANALYTICS SYSTEM
        self.analytics = {
            # Position-based view tracking
            'when_top': {},           # {'14': [45,52,48], '15': [38,42]}
            'when_not_top': {},       # {'14': [18,22,15], '15': [12,15]}
            
            # Performance metrics
            'peak_hours': [],         # [16,14,15] - top performing hours
            'low_view_hours': [],     # [1,2,5] - hours to skip bidding
            'performance_boost': {},  # {'14': 136, '15': 180} - % boost
            
            # Tracking data
            'bid_attempts': 0,
            'bid_successes': 0,
            'today_views': 0,
            'last_calculation': None,
            
            # IP information
            'render_ip': 'Unknown'
        }
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'credits_saved': 0
        }
        
        # Get Render IP on startup
        self.get_render_ip()

    def rotate_user_agent(self):
        user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def get_render_ip(self):
        """Get and store Render's current IP address"""
        try:
            response = requests.get('https://httpbin.org/ip', timeout=10)
            ip_data = response.json()
            self.analytics['render_ip'] = ip_data['origin']
            logger.info(f"🌐 Render IP: {self.analytics['render_ip']}")
        except Exception as e:
            logger.error(f"IP check failed: {e}")

    def human_delay(self, min_seconds=2, max_seconds=5):
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def force_login(self):
        """Smart login with dynamic password field detection"""
        try:
            logger.info("🔄 Logging in...")
            self.human_delay(2, 4)
            
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.error("❌ Login form not found!")
                return False
                
            action_path = form.get('action', '')
            post_url = f"https://adsha.re{action_path}" if not action_path.startswith('http') else action_path
            
            # DYNAMIC PASSWORD FIELD DETECTION
            password_field = None
            for field in form.find_all('input'):
                field_name = field.get('name', '')
                field_value = field.get('value', '')
                if field_value == 'Password' and field_name != 'mail' and field_name:
                    password_field = field_name
                    break
            
            if not password_field:
                logger.error("❌ Could not find password field!")
                return False
            
            login_data = {
                'mail': self.email,
                password_field: self.password
            }
            
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            self.human_delay(1, 2)
            
            if self.check_session_valid():
                self.session_valid = True
                self.stats['logins_made'] += 1
                logger.info("✅ Login successful!")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

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

    def smart_login(self):
        if self.check_session_valid():
            self.session_valid = True
            return True
        return self.force_login()

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
        except:
            return 0

    def get_visitor_credits(self):
        """Fixed comma parsing for visitor credits"""
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            visitors_match = re.search(r'Visitors:\s*([\d,]+)', soup.get_text())
            if visitors_match:
                visitors_str = visitors_match.group(1).replace(',', '')
                return int(visitors_str)
            return 0
        except:
            return 0

    def check_credit_safety(self):
        """Credit safety - SEPARATE from campaign loading"""
        self.current_traffic_credits = self.get_traffic_credits()
        self.current_visitor_credits = self.get_visitor_credits()
        
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

    def update_analytics_data(self, campaign_name, is_top_bidder, current_views):
        """Track detailed analytics for smart strategy"""
        current_hour = datetime.now().hour
        
        if campaign_name in self.campaigns:
            campaign_data = self.campaigns[campaign_name]
            if 'last_views_count' not in campaign_data:
                campaign_data['last_views_count'] = current_views
                return
            
            views_increase = current_views - campaign_data['last_views_count']
            if views_increase > 0:
                self.analytics['today_views'] += views_increase
                
                # Track views by position
                hour_str = str(current_hour)
                if is_top_bidder:
                    if hour_str not in self.analytics['when_top']:
                        self.analytics['when_top'][hour_str] = []
                    self.analytics['when_top'][hour_str].append(views_increase)
                else:
                    if hour_str not in self.analytics['when_not_top']:
                        self.analytics['when_not_top'][hour_str] = []
                    self.analytics['when_not_top'][hour_str].append(views_increase)
            
            campaign_data['last_views_count'] = current_views

    def calculate_smart_strategy(self):
        """Calculate peak hours, low-view hours, and performance boosts"""
        if len(self.analytics['when_top']) < 4:  # Need minimum data
            return
        
        hourly_performance = {}
        
        # Calculate average views per hour for both positions
        for hour in range(24):
            hour_str = str(hour)
            top_views = self.analytics['when_top'].get(hour_str, [])
            not_top_views = self.analytics['when_not_top'].get(hour_str, [])
            
            if top_views and not_top_views:
                avg_top = sum(top_views) / len(top_views)
                avg_not_top = sum(not_top_views) / len(not_top_views)
                
                # Calculate performance boost
                if avg_not_top > 0:
                    boost = ((avg_top - avg_not_top) / avg_not_top) * 100
                    hourly_performance[hour] = {
                        'avg_top': avg_top,
                        'avg_not_top': avg_not_top,
                        'boost': boost
                    }
        
        if not hourly_performance:
            return
        
        # Calculate overall average for threshold
        all_top_views = []
        for views in self.analytics['when_top'].values():
            all_top_views.extend(views)
        
        overall_avg = sum(all_top_views) / len(all_top_views) if all_top_views else 0
        
        # Identify peak hours (top 4 by boost)
        sorted_by_boost = sorted(hourly_performance.items(), key=lambda x: x[1]['boost'], reverse=True)
        self.analytics['peak_hours'] = [hour for hour, _ in sorted_by_boost[:4]]
        
        # Identify low-view hours (below 50% of average)
        self.analytics['low_view_hours'] = []
        for hour, data in hourly_performance.items():
            if data['avg_top'] < overall_avg * 0.5:
                self.analytics['low_view_hours'].append(hour)
        
        # Store performance boosts
        self.analytics['performance_boost'] = {str(hour): data['boost'] for hour, data in hourly_performance.items()}
        self.analytics['last_calculation'] = datetime.now().isoformat()
        
        logger.info(f"🎯 Strategy Updated - Peak: {self.analytics['peak_hours']}, Low: {self.analytics['low_view_hours']}")

    def should_skip_bidding(self):
        """Check if current hour is low-view hour"""
        current_hour = datetime.now().hour
        if current_hour in self.analytics['low_view_hours']:
            logger.info(f"⏸️ Skipping bid - low views at {current_hour}:00")
            return True
        return False

    def calculate_smart_frequency(self):
        """Smart frequency with peak hours and low-view skipping"""
        current_hour = datetime.now().hour
        
        # Skip bidding during low-view hours
        if self.should_skip_bidding():
            return random.randint(1800, 3600)  # 30-60 min checks when skipping
        
        # Aggressive during peak hours
        if current_hour in self.analytics['peak_hours']:
            self.frequency_modes['current_mode'] = 'aggressive'
            return random.randint(120, 180)
        
        # Normal logic
        target = self.top_bidder_tracking['daily_target_minutes']
        current = self.top_bidder_tracking['current_minutes_today']
        
        if current < target * 0.7:
            self.frequency_modes['current_mode'] = 'aggressive'
            return random.randint(120, 180)
        else:
            self.frequency_modes['current_mode'] = 'conservative'
            return random.randint(900, 1200)

    def send_telegram(self, message, parse_mode='HTML'):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": message, "parse_mode": parse_mode}
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
        elif command_lower == '/strategy':
            self.send_strategy_report()
        elif command_lower == '/progress':
            self.send_top_bidder_progress()
        elif command_lower == '/backup':
            self.backup_analytics()
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

🌐 RENDER IP: {self.analytics['render_ip']}
💰 CREDITS: Traffic {traffic_credits} | Visitors {visitor_credits:,}

⏱️ TOP BIDDER: {current//60}h {current%60}m / {target//60}h {target%60}m ({progress_percent:.1f}%)
🎯 MODE: {self.frequency_modes['current_mode']}
🏆 POSITION: {top_campaigns}/{total_campaigns} at #1

{campaigns_list}
🤖 Auto Bids: {self.stats['auto_bids_made']}
"""
        self.send_telegram(status_msg)

    def send_analytics_report(self):
        self.calculate_smart_strategy()  # Ensure latest calculations
        
        if not self.analytics['peak_hours']:
            self.send_telegram("📊 Collecting analytics data... check back in a few hours")
            return

        # Format peak hours
        peak_hours_str = ", ".join([f"{h}:00" for h in self.analytics['peak_hours']])
        
        # Format low-view hours
        low_view_str = ", ".join([f"{h}:00" for h in self.analytics['low_view_hours']]) if self.analytics['low_view_hours'] else "None"
        
        # Calculate performance metrics
        bid_success_rate = (self.analytics['bid_successes'] / self.analytics['bid_attempts'] * 100) if self.analytics['bid_attempts'] > 0 else 0
        
        analytics_msg = f"""
📈 SMART ANALYTICS

🌐 RENDER IP: {self.analytics['render_ip']}
🕐 PEAK HOURS: {peak_hours_str}
⏸️ LOW-VIEW HOURS: {low_view_str}
📊 DATA POINTS: {len(self.analytics['when_top'])} hours tracked

📈 PERFORMANCE BOOST:
"""
        
        # Add top 3 performing hours
        for hour in self.analytics['peak_hours'][:3]:
            boost = self.analytics['performance_boost'].get(str(hour), 0)
            analytics_msg += f"   {hour}:00 → +{boost:.1f}% boost\n"
        
        analytics_msg += f"""
🎯 BID SUCCESS: {bid_success_rate:.1f}%
📊 TODAY'S VIEWS: {self.analytics['today_views']:,}
"""
        self.send_telegram(analytics_msg)

    def send_strategy_report(self):
        current_hour = datetime.now().hour
        current_mode = "AGGRESSIVE" if current_hour in self.analytics['peak_hours'] else "CONSERVATIVE"
        skipping = "YES" if current_hour in self.analytics['low_view_hours'] else "NO"
        
        strategy_msg = f"""
🎯 CURRENT STRATEGY

🌐 RENDER IP: {self.analytics['render_ip']}
🕐 CURRENT HOUR: {current_hour}:00
⚡ MODE: {current_mode}
⏸️ SKIPPING: {skipping}

📊 STRATEGY BREAKDOWN:
• Aggressive: {len(self.analytics['peak_hours'])} hours
• Conservative: {24 - len(self.analytics['peak_hours']) - len(self.analytics['low_view_hours'])} hours  
• Skipping: {len(self.analytics['low_view_hours'])} hours

💰 EFFICIENCY: Saving ~{len(self.analytics['low_view_hours'])*4}% credits via smart skipping
"""
        self.send_telegram(strategy_msg)

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

    def backup_analytics(self):
        """Backup analytics data via Telegram"""
        backup_data = json.dumps(self.analytics, indent=2)
        self.send_telegram(f"📊 ANALYTICS BACKUP:\n```{backup_data}```")
        self.send_telegram("✅ Backup completed!")

    def send_help(self):
        help_msg = """
🤖 ULTIMATE SMART BIDDER

/start - Start monitoring
/stop - Stop monitoring  
/status - Credits, bids & IP
/campaigns - List campaigns
/analytics - Performance analytics
/strategy - Current bidding strategy
/progress - Top bidder progress
/backup - Backup analytics data

💡 SMART FEATURES:
• Auto peak hour detection
• Low-view hour skipping
• Dynamic login system
• IP monitoring
• Credit protection
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

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        try:
            # Track bid attempt
            self.analytics['bid_attempts'] += 1
            
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
                self.analytics['bid_successes'] += 1
                
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

    def check_all_campaigns(self):
        if not self.is_monitoring:
            return
            
        self.stats['checks_made'] += 1
        
        if not self.smart_login():
            return
        
        try:
            # ALWAYS LOAD CAMPAIGNS FIRST (regardless of credits)
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
            
            # Check credits SEPARATELY - only affects bidding, not campaign operations
            credit_safe = self.check_credit_safety()
            
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
                    
                    # Update performance analytics - CRITICAL FOR PEAK HOUR CALCULATION
                    self.update_analytics_data(campaign_name, is_top_bidder, campaign_data['views']['current'])
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}, Top: {is_top_bidder}")
                    
                    # Smart auto-bid logic - ONLY AFFECTED BY CREDIT SAFETY
                    if (credit_safe and campaign_data['auto_bid'] and 
                        not self.should_skip_bid_with_random_hold(campaign_name)):
                        
                        self.execute_smart_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Check error: {e}")

    def update_top_bidder_tracking(self, campaign_name, is_top_bidder):
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

    def reset_daily_target_if_needed(self):
        today = datetime.now().date()
        if today != self.top_bidder_tracking['last_reset_date']:
            self.top_bidder_tracking = {
                'daily_target_minutes': random.randint(360, 480),
                'current_minutes_today': 0,
                'last_reset_date': today,
                'current_session_start': None,
                'is_currently_top': False
            }
            logger.info(f"🔄 New daily target: {self.top_bidder_tracking['daily_target_minutes']} minutes")
            self.send_telegram(f"🎯 New Daily Target: {self.top_bidder_tracking['daily_target_minutes']//60}h {self.top_bidder_tracking['daily_target_minutes']%60}m")

    def run(self):
        logger.info("🤖 Starting Ultimate Smart Bidder...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!")
        
        last_command_check = 0
        last_campaign_check = 0
        last_strategy_calculation = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Process commands
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Recalculate strategy every 6 hours
                if current_time - last_strategy_calculation >= 21600:  # 6 hours
                    self.calculate_smart_strategy()
                    last_strategy_calculation = current_time
                
                # Reset daily target if needed
                self.reset_daily_target_if_needed()
                
                # Campaign checking
                if self.is_monitoring:
                    check_interval = self.calculate_smart_frequency()
                    
                    if current_time - last_campaign_check >= check_interval:
                        self.check_all_campaigns()
                        last_campaign_check = current_time
                        
                        mode = self.frequency_modes['current_mode']
                        logger.info(f"🔄 Check complete. Next in {check_interval//60}min ({mode} mode)")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

# Flask routes
@app.route('/')
def home():
    return "🤖 Ultimate Smart Bidder - Active"

@app.route('/health')
def health():
    return "✅ Bot Healthy"

@app.route('/ip')
def show_ip():
    bot = getattr(app, 'bot_instance', None)
    if bot:
        return f"🌐 Render IP: {bot.analytics.get('render_ip', 'Unknown')}"
    return "❌ Bot not initialized"

def run_bot():
    bot = UltimateSmartBidder()
    app.bot_instance = bot  # Make bot accessible to routes
    bot.run()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    app.run(host='0.0.0.0', port=10000, debug=False)
