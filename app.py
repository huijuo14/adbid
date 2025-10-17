import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime, timedelta
import os
import json
import pytz

# Enhanced logging setup for Railway
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
        self.campaign_progress_history = {}  # For predictions
        self.last_alert_time = 0
        self.last_save_time = 0
        self.current_global_bid = 0
        self.sent_alerts = {}
        self.gist_id = None
        
        # Timing
        self.check_interval = 300  # 5 minutes
        self.bid_cooldown = 60
        
        # Load saved data
        if self.github_token:
            self.load_from_github()
        else:
            logger.warning("GIST: No token - persistence disabled")
        
        logger.info("🚀 SMART_BIDDER: Initialized with hybrid prediction engine")

    def rotate_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
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
            logger.warning("GIST_SAVE: No token - skipping")
            return False
            
        try:
            data = {
                'bid_history': self.bid_history,
                'campaigns': self.campaigns,
                'campaign_progress_history': self.serialize_progress_history(),
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
            if self.gist_id:
                logger.info(f"GIST_SAVE: Updating gist {self.gist_id}")
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
                logger.error(f"GIST_SAVE: Failed - {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"GIST_SAVE: Error - {e}")
            return False

    def serialize_progress_history(self):
        """Convert progress history to serializable format"""
        serialized = {}
        for campaign, history in self.campaign_progress_history.items():
            serialized[campaign] = []
            for entry in history:
                serialized_entry = entry.copy()
                if 'timestamp' in entry and isinstance(entry['timestamp'], datetime):
                    serialized_entry['timestamp'] = entry['timestamp'].isoformat()
                serialized[campaign].append(serialized_entry)
        return serialized

    def load_from_github(self):
        """Load data from GitHub Gist"""
        if not self.github_token:
            logger.warning("GIST_LOAD: No token - skipping")
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.github_token}",
                "Content-Type": "application/json"
            }
            
            url = "https://api.github.com/gists"
            logger.info("GIST_LOAD: Searching for gists...")
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                gists = response.json()
                bidbot_gist = None
                
                for gist in gists:
                    if 'bidbot_data.json' in gist.get('files', {}):
                        bidbot_gist = gist
                        self.gist_id = gist['id']
                        logger.info(f"GIST_LOAD: Found gist: {self.gist_id}")
                        break
                
                if bidbot_gist:
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
                            logger.info(f"GIST_LOAD: Restored {restored_count} bid records")
                        
                        # Restore campaigns
                        if 'campaigns' in data:
                            restored_campaigns = 0
                            for campaign_name, campaign_data in data['campaigns'].items():
                                self.campaigns[campaign_name] = campaign_data
                                restored_campaigns += 1
                            logger.info(f"GIST_LOAD: Restored {restored_campaigns} campaigns")
                        
                        # Restore progress history
                        if 'campaign_progress_history' in data:
                            restored_history = 0
                            for campaign, history in data['campaign_progress_history'].items():
                                self.campaign_progress_history[campaign] = []
                                for entry in history:
                                    if 'timestamp' in entry and isinstance(entry['timestamp'], str):
                                        try:
                                            entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                                        except:
                                            entry['timestamp'] = self.get_ist_time()
                                    self.campaign_progress_history[campaign].append(entry)
                                    restored_history += 1
                            logger.info(f"GIST_LOAD: Restored {restored_history} progress records")
                        
                        # Restore settings
                        if 'max_bid_limit' in data:
                            self.max_bid_limit = data['max_bid_limit']
                        if 'auto_bid_enabled' in data:
                            self.auto_bid_enabled = data['auto_bid_enabled']
                        if 'current_global_bid' in data:
                            self.current_global_bid = data['current_global_bid']
                        
                        logger.info("GIST_LOAD: Data restoration completed")
                        return True
                else:
                    logger.info("GIST_LOAD: No existing gist found - fresh start")
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
            
            logger.error("LOGIN: Failed - invalid credentials")
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

    def update_progress_history(self, campaign_name, current_views, total_views):
        """Update progress history for predictions"""
        try:
            if campaign_name not in self.campaign_progress_history:
                self.campaign_progress_history[campaign_name] = []
            
            current_time = self.get_ist_time()
            new_entry = {
                'timestamp': current_time,
                'current_views': current_views,
                'total_views': total_views,
                'completion_pct': (current_views / total_views * 100) if total_views > 0 else 0
            }
            
            # Add new entry
            self.campaign_progress_history[campaign_name].append(new_entry)
            
            # Keep only last 12 entries (1 hour of data at 5-min intervals)
            if len(self.campaign_progress_history[campaign_name]) > 12:
                self.campaign_progress_history[campaign_name] = self.campaign_progress_history[campaign_name][-12:]
            
            logger.info(f"📊 PROGRESS_HISTORY: Updated '{campaign_name}' - {current_views}/{total_views} views")
            
        except Exception as e:
            logger.error(f"PROGRESS_HISTORY: Error - {e}")

    def calculate_completion_prediction(self, campaign_name, current_views, total_views):
        """Hybrid multi-window prediction in views per minute"""
        try:
            if campaign_name not in self.campaign_progress_history:
                return "No data yet"
            
            history = self.campaign_progress_history[campaign_name]
            if len(history) < 2:
                return "Collecting data..."
            
            current_time = self.get_ist_time()
            completion_pct = (current_views / total_views * 100) if total_views > 0 else 0
            
            # Define windows (in minutes)
            short_window = 10
            medium_window = 20
            long_window = 30
            
            # Calculate velocities for each window
            short_velocity = self.calculate_velocity(history, short_window, current_time)
            medium_velocity = self.calculate_velocity(history, medium_window, current_time)
            long_velocity = self.calculate_velocity(history, long_window, current_time)
            
            # Adaptive weights based on completion percentage
            if completion_pct < 80:
                weights = [0.2, 0.3, 0.5]  # Long window favored for early stages
            elif completion_pct < 95:
                weights = [0.4, 0.4, 0.2]  # Balanced for mid stages
            else:
                weights = [0.6, 0.3, 0.1]  # Short window favored for final stages
            
            # Calculate weighted average velocity (views per minute)
            weighted_velocity = (short_velocity * weights[0] + 
                               medium_velocity * weights[1] + 
                               long_velocity * weights[2])
            
            if weighted_velocity <= 0:
                return "Stalled"
            
            # Calculate remaining time
            remaining_views = total_views - current_views
            if remaining_views <= 0:
                return "Completed"
            
            minutes_remaining = remaining_views / weighted_velocity
            predicted_end = current_time + timedelta(minutes=minutes_remaining)
            
            # Format prediction
            if minutes_remaining < 60:
                time_str = f"{int(minutes_remaining)} min"
            else:
                hours = int(minutes_remaining // 60)
                mins = int(minutes_remaining % 60)
                time_str = f"{hours}h {mins}m"
            
            prediction_str = f"{self.format_ist_time(predicted_end)} IST ({time_str})"
            
            logger.info(f"🎯 PREDICTION_HYBRID: '{campaign_name}' - {completion_pct:.1f}% - {weighted_velocity:.2f} views/min - ETA: {prediction_str}")
            
            return prediction_str
            
        except Exception as e:
            logger.error(f"PREDICTION: Error - {e}")
            return "Error calculating"

    def calculate_velocity(self, history, window_minutes, current_time):
        """Calculate views per minute for given time window"""
        try:
            window_start = current_time - timedelta(minutes=window_minutes)
            
            # Find data points within the window
            relevant_data = []
            for entry in reversed(history):  # Start from most recent
                if entry['timestamp'] >= window_start:
                    relevant_data.append(entry)
                else:
                    break
            
            if len(relevant_data) < 2:
                return 0
            
            # Use oldest and newest in window
            oldest = relevant_data[-1]
            newest = relevant_data[0]
            
            views_gained = newest['current_views'] - oldest['current_views']
            time_diff = (newest['timestamp'] - oldest['timestamp']).total_seconds() / 60  # in minutes
            
            if time_diff <= 0:
                return 0
            
            velocity = views_gained / time_diff  # views per minute
            return max(0, velocity)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"VELOCITY_CALC: Error for {window_minutes}min window - {e}")
            return 0

    def parse_campaigns_real_time(self):
        """Real-time parsing for /status command"""
        try:
            logger.info("PARSING_REALTIME: Fresh scrape started...")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*'))
            logger.info(f"PARSING_REALTIME: Found {len(campaign_divs)} campaign divs")
            
            for i, div in enumerate(campaign_divs):
                try:
                    # Extract campaign name
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
                    
                    # Update progress history for predictions
                    self.update_progress_history(campaign_name, current_views, total_views)
                    
                    # Calculate prediction
                    prediction = self.calculate_completion_prediction(campaign_name, current_views, total_views)
                    
                    # Get auto-bid setting
                    auto_bid = self.campaigns.get(campaign_name, {}).get('auto_bid', False)
                    
                    campaigns[campaign_name] = {
                        'your_bid': your_bid,
                        'top_bid': self.current_global_bid,
                        'auto_bid': auto_bid,
                        'progress': f"{current_views:,}/{total_views:,}",
                        'current_views': current_views,
                        'total_views': total_views,
                        'completion_pct': (current_views / total_views * 100) if total_views > 0 else 0,
                        'completed': completed,
                        'active': active,
                        'status': 'COMPLETED' if completed else 'ACTIVE' if active else 'UNKNOWN',
                        'prediction': prediction,
                        'last_checked': self.get_ist_time()
                    }
                    
                except Exception as e:
                    logger.error(f"PARSING_REALTIME: Error parsing div {i} - {e}")
                    continue
            
            logger.info(f"PARSING_REALTIME: Successfully parsed {len(campaigns)} campaigns")
            return campaigns
            
        except Exception as e:
            logger.error(f"PARSING_REALTIME: Error - {e}")
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
        
        # Only alert if bid drops by more than 50 credits
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
            self.send_enhanced_status_real_time()
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
        self.send_telegram("🚀 SMART BIDDER ACTIVATED!\n\n24/7 monitoring with hybrid prediction engine!")

    def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("MONITORING: Stopped")
        self.send_telegram("🛑 Monitoring STOPPED")

    def send_enhanced_status_real_time(self):
        """Real-time status with fresh scraping"""
        logger.info("STATUS_REALTIME: Generating real-time status...")
        
        if not self.smart_login():
            self.send_telegram("❌ Cannot fetch status - login failed")
            return
        
        # Fresh scrape for real-time data
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
        
        # Get fresh campaign data
        campaigns = self.parse_campaigns_real_time()
        self.campaigns.update(campaigns)  # Merge with existing data
        
        status_msg = f"""
📊 REAL-TIME STATUS REPORT

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
                
                # Add prediction if available
                prediction = data.get('prediction', 'Calculating...')
                
                status_msg += f"{position} {status_icon} {name}\n"
                status_msg += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {status}\n"
                status_msg += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
                status_msg += f"   🎯 Predicted End: {prediction}\n\n"
        else:
            status_msg += "No campaigns detected yet. Checking adverts page...\n\n"

        status_msg += f"🕒 {current_time} IST | 🤖 Real-time data"
        self.send_telegram(status_msg)
        logger.info("STATUS_REALTIME: Sent real-time status")

    def send_campaigns_list(self):
        """Detailed campaign list with predictions"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns found yet. The bot is checking adverts page...")
            return
        
        campaigns_text = "📋 YOUR CAMPAIGNS\n\n"
        
        for name, data in self.campaigns.items():
            auto_status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
            position = "🏆 #1" if data.get('your_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
            status_icon = "✅ COMPLETED" if data.get('completed') else "🟢 ACTIVE" if data.get('active') else "⚪ UNKNOWN"
            prediction = data.get('prediction', 'Calculating...')
            
            campaigns_text += f"{position} <b>{name}</b>\n"
            campaigns_text += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {auto_status}\n"
            campaigns_text += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
            campaigns_text += f"   🎯 Predicted End: {prediction}\n"
            campaigns_text += f"   📊 Status: {status_icon}\n\n"
        
        campaigns_text += "💡 Use /auto [campaign] on/off to control auto-bidding"
        self.send_telegram(campaigns_text)

    def send_bid_history(self):
        """Clean bid history - only show actual changes"""
        if not self.bid_history:
            self.send_telegram("📊 No bid history yet. Monitoring in progress...")
            return
        
        # Filter to only show actual bid changes
        filtered_history = []
        last_bid = None
        
        for record in self.bid_history:
            current_bid = record['bid']
            if current_bid != last_bid:
                filtered_history.append(record)
                last_bid = current_bid
        
        if not filtered_history:
            self.send_telegram("📊 No bid changes recorded yet.")
            return
        
        history_msg = "📈 GLOBAL BID HISTORY (Changes only):\n\n"
        
        for record in filtered_history[-10:]:  # Last 10 changes
            if 'time' in record and isinstance(record['time'], datetime):
                time_str = self.format_ist_time(record['time'])
            else:
                time_str = "Unknown"
            history_msg += f"🕒 {time_str} - {record['bid']} credits\n"
        
        # Add current bid info
        if filtered_history:
            current_bid = filtered_history[-1]['bid']
            if len(filtered_history) >= 2:
                previous_bid = filtered_history[-2]['bid']
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
/status - Real-time status with predictions
/campaigns - List all campaigns with ETAs
/bids - Clean bid history (changes only)
/target [amount] - Set max bid limit
/autobid on/off - Auto-bid for all campaigns
/auto [campaign] on/off - Auto-bid for specific campaign

🎯 NEW FEATURES:
• Real-time status with fresh scraping
• Hybrid ETA predictions (multi-window)
• Clean bid history (changes only)
• Fixed 99% completion alerts
• Enhanced Railway logging
"""
        self.send_telegram(help_msg)

    def check_completion_alerts(self):
        """Check and send completion alerts"""
        try:
            for campaign_name, campaign_data in self.campaigns.items():
                completion_pct = campaign_data.get('completion_pct', 0)
                
                # Check for 99% completion alert
                if 99.0 <= completion_pct < 100.0:
                    alert_key = f"99pct_{campaign_name}"
                    if alert_key not in self.sent_alerts:
                        message = f"🚨 CAMPAIGN NEARING COMPLETION!\n\n\"{campaign_name}\"\n📈 Progress: {campaign_data['progress']} ({completion_pct:.1f}%)\n\n⏰ EXTEND SOON - Will complete shortly!"
                        self.send_telegram(message)
                        self.sent_alerts[alert_key] = True
                        logger.info(f"COMPLETION_ALERT: Sent 99% alert for {campaign_name}")
                
                # Check for 100% completion alert
                if completion_pct >= 99.9 and campaign_data.get('completed'):
                    alert_key = f"completed_{campaign_name}"
                    if alert_key not in self.sent_alerts:
                        message = f"✅ CAMPAIGN COMPLETED!\n\n\"{campaign_name}\"\n📈 Progress: {campaign_data['progress']} (100%)\n\n🚨 EXTEND NOW - Bid reset to 0!"
                        self.send_telegram(message)
                        self.sent_alerts[alert_key] = True
                        logger.info(f"COMPLETION_ALERT: Sent 100% alert for {campaign_name}")
                        
        except Exception as e:
            logger.error(f"COMPLETION_ALERT: Error - {e}")

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
                    prediction = data.get('prediction', 'Calculating...')
                    status_msg += f"{position} {status_icon} \"{name}\" - {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
                    status_msg += f"   🎯 ETA: {prediction}\n"
        
        if self.bid_history:
            # Get last bid change
            last_change = None
            current_bid = self.bid_history[-1]['bid'] if self.bid_history else 0
            for i in range(len(self.bid_history)-2, -1, -1):
                if self.bid_history[i]['bid'] != current_bid:
                    last_change = self.bid_history[i]
                    break
            
            if last_change:
                change = current_bid - last_change['bid']
                change_icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                status_msg += f"\n{change_icon} Last Bid Change: {last_change['bid']} → {current_bid} ({change:+d} credits)"
        
        status_msg += "\n\n🤖 Hybrid prediction engine active..."
        
        self.send_telegram(status_msg)
        logger.info("HOURLY_STATUS: Sent automatic report")

    def check_and_alert(self):
        """Main monitoring function with hybrid predictions"""
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("MONITORING: Cannot check - login failed")
            return
        
        # Get global top bid
        global_top_bid = self.get_global_top_bid()
        
        if global_top_bid > 0:
            # Only record bid if it changed
            if not self.bid_history or self.bid_history[-1]['bid'] != global_top_bid:
                self.bid_history.append({
                    'bid': global_top_bid,
                    'time': self.get_ist_time(),
                    'type': 'global'
                })
                logger.info(f"💰 BID_UPDATE: Global bid changed to {global_top_bid} credits - recorded in history")
            
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
        
        # Parse campaigns with updated global bid and predictions
        new_campaigns = self.parse_campaigns_real_time()
        
        # Update campaigns with global top bid
        for campaign_name in new_campaigns:
            new_campaigns[campaign_name]['top_bid'] = self.current_global_bid
        
        self.campaigns.update(new_campaigns)
        
        # Check for completion alerts
        self.check_completion_alerts()
        
        # Auto-save to GitHub Gist every hour
        if time.time() - self.last_save_time > 3600:
            self.save_to_github()

    def run(self):
        logger.info("🚀 Starting Smart Bidder with hybrid prediction engine...")
        
        if not self.force_login():
            logger.error("❌ Failed to start - login failed")
            return
        
        # Initialize sent alerts if not loaded
        if not hasattr(self, 'sent_alerts'):
            self.sent_alerts = {}
        
        startup_msg = f"🤖 SMART BIDDER STARTED!\n• Hybrid prediction engine\n• Real-time status\n• Clean bid history\n• Enhanced logging\nType /help for commands"
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
                    logger.info("🔍 Performing scheduled check with predictions...")
                    self.check_and_alert()
                    last_check = current_time
                    logger.info("✅ Check completed with predictions")
                
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