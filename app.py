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

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

class UltimateBidder:
    def __init__(self):
        # Environment variables
        self.bot_token = os.environ.get('BOT_TOKEN', "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc")
        self.chat_id = os.environ.get('CHAT_ID', "2052085789")
        self.email = os.environ.get('EMAIL', "jiocloud90@gmail.com")
        self.password = os.environ.get('PASSWORD', "@Sd2007123")
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.last_update_id = 0
        
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        # Monitoring settings
        self.is_monitoring = True  # Auto-start monitoring
        self.auto_bid_enabled = False
        self.max_bid_limit = 100
        
        # Bidding parameters from second script
        self.minimal_bid_weights = [1, 2]
        self.bid_cooldown = 60  # Cooldown in seconds between bids
        self.last_bid_time = {}  # For rate-limiting bids
        
        # Credit Protection Settings
        self.visitor_alert_threshold = 1000
        self.visitor_stop_threshold = 500
        self.current_traffic_credits = 0
        self.current_visitor_credits = 0
        self.last_credit_alert = None
        
        # Data storage - BOMB PREDICTOR EDITION
        self.bid_history = []
        self.campaigns = {}
        self.campaign_progress_history = {}
        self.completed_campaigns = {}
        self.learning_data = {
            'position_speeds': {
                'top_speed_samples': [],
                'not_top_speed_samples': [],
                'top_speed_avg': 0,
                'not_top_speed_avg': 0,
                'confidence_score': 0.0
            },
            'burst_patterns': {},
            'time_patterns': {
                'hourly_speeds': {},
                'daily_speeds': {}
            },
            'campaign_profiles': {},
            'prediction_accuracy': []
        }
        self.last_alert_time = 0
        self.last_save_time = 0
        self.current_global_bid = 0
        self.sent_alerts = {}
        self.gist_id = None
        
        # Timing
        self.check_interval = 300  # 5 minutes
        
        # Load saved data
        if self.github_token:
            self.load_from_github()
        else:
            logger.warning("GIST: No token - persistence disabled")
        
        logger.info("💣 ULTIMATE BOMB PREDICTOR: Initialized!")

    def rotate_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
        ]
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def get_ist_time(self):
        ist = pytz.timezone('Asia/Kolkata')
        return datetime.now(ist)

    def format_ist_time(self, dt=None):
        if dt is None:
            dt = self.get_ist_time()
        return dt.strftime("%I:%M %p")

    def human_delay(self, min_seconds=1, max_seconds=3):
        time.sleep(random.uniform(min_seconds, max_seconds))

    # === PERSISTENCE METHODS ===
    def serialize_bid_history(self):
        """Convert bid history to JSON-serializable format"""
        serialized = []
        for item in self.bid_history:
            serialized_item = item.copy()
            if 'time' in serialized_item and isinstance(serialized_item['time'], datetime):
                serialized_item['time'] = serialized_item['time'].isoformat()
            serialized.append(serialized_item)
        return serialized

    def serialize_campaigns(self):
        """Convert campaigns to JSON-serializable format"""
        serialized = {}
        for campaign, data in self.campaigns.items():
            serialized[campaign] = data.copy()
            if 'last_checked' in serialized[campaign] and isinstance(serialized[campaign]['last_checked'], datetime):
                serialized[campaign]['last_checked'] = serialized[campaign]['last_checked'].isoformat()
        return serialized

    def serialize_completed_campaigns(self):
        """Convert completed campaigns to JSON-serializable format"""
        serialized = {}
        for campaign, data in self.completed_campaigns.items():
            serialized[campaign] = data.copy()
            if 'completed_time' in serialized[campaign] and isinstance(serialized[campaign]['completed_time'], datetime):
                serialized[campaign]['completed_time'] = serialized[campaign]['completed_time'].isoformat()
        return serialized

    def serialize_learning_data(self):
        """Convert learning data to JSON-serializable format"""
        serialized = self.learning_data.copy()
        
        # Handle burst patterns datetime objects
        if 'burst_patterns' in serialized:
            for campaign, burst_data in serialized['burst_patterns'].items():
                if 'burst_times' in burst_data:
                    serialized['burst_patterns'][campaign]['burst_times'] = [
                        t.isoformat() if isinstance(t, datetime) else t 
                        for t in burst_data['burst_times']
                    ]
                if 'first_detection' in burst_data and isinstance(burst_data['first_detection'], datetime):
                    serialized['burst_patterns'][campaign]['first_detection'] = burst_data['first_detection'].isoformat()
        
        return serialized

    def serialize_sent_alerts(self):
        """Convert sent alerts to JSON-serializable format"""
        serialized = {}
        for alert_key, alert_data in self.sent_alerts.items():
            if isinstance(alert_data, dict):
                serialized[alert_key] = alert_data.copy()
                for key, value in serialized[alert_key].items():
                    if isinstance(value, datetime):
                        serialized[alert_key][key] = value.isoformat()
            else:
                serialized[alert_key] = alert_data
        return serialized

    def save_to_github(self):
        """Save ALL data to GitHub Gist with proper JSON serialization"""
        if not self.github_token:
            return False
            
        try:
            # Create a serializable copy of the data
            data = {
                'bid_history': self.serialize_bid_history(),
                'campaigns': self.serialize_campaigns(),
                'completed_campaigns': self.serialize_completed_campaigns(),
                'campaign_progress_history': self.serialize_progress_history(),
                'learning_data': self.serialize_learning_data(),
                'max_bid_limit': self.max_bid_limit,
                'auto_bid_enabled': self.auto_bid_enabled,
                'current_global_bid': self.current_global_bid,
                'sent_alerts': self.serialize_sent_alerts(),
                'last_save': datetime.now().isoformat(),
                'gist_id': self.gist_id
            }
            
            gist_data = {
                "description": f"💣 BOMB PREDICTOR - {datetime.now().isoformat()}",
                "public": False,
                "files": {
                    "bomb_predictor.json": {
                        "content": json.dumps(data, indent=2)
                    }
                }
            }
            
            headers = {"Authorization": f"token {self.github_token}"}
            url = "https://api.github.com/gists"
            
            if self.gist_id:
                url = f"https://api.github.com/gists/{self.gist_id}"
                response = self.session.patch(url, json=gist_data, headers=headers, timeout=30)
            else:
                response = self.session.post(url, json=gist_data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                self.gist_id = response.json().get('id')
                self.last_save_time = time.time()
                logger.info("💾 GIST_SAVE: All bomb predictor data saved!")
                return True
            return False
                
        except Exception as e:
            logger.error(f"GIST_SAVE: Error - {e}")
            return False

    def serialize_progress_history(self):
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
        if not self.github_token:
            return False
            
        try:
            headers = {"Authorization": f"token {self.github_token}"}
            url = "https://api.github.com/gists"
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                gists = response.json()
                for gist in gists:
                    if 'bomb_predictor.json' in gist.get('files', {}):
                        self.gist_id = gist['id']
                        gist_url = gist['files']['bomb_predictor.json']['raw_url']
                        data_response = self.session.get(gist_url, timeout=30)
                        
                        if data_response.status_code == 200:
                            data = json.loads(data_response.text)
                            logger.info("💾 GIST_LOAD: Restoring bomb predictor data...")
                            
                            # Restore ALL data structures
                            if 'bid_history' in data:
                                for item in data['bid_history']:
                                    if 'time' in item and isinstance(item['time'], str):
                                        try:
                                            item['time'] = datetime.fromisoformat(item['time'].replace('Z', '+00:00'))
                                        except:
                                            item['time'] = self.get_ist_time()
                                self.bid_history = data['bid_history']
                            
                            self.campaigns = data.get('campaigns', {})
                            self.completed_campaigns = data.get('completed_campaigns', {})
                            self.learning_data = data.get('learning_data', self.learning_data)
                            self.sent_alerts = data.get('sent_alerts', {})
                            
                            # Restore datetime objects in campaigns
                            for campaign, campaign_data in self.campaigns.items():
                                if 'last_checked' in campaign_data and isinstance(campaign_data['last_checked'], str):
                                    try:
                                        self.campaigns[campaign]['last_checked'] = datetime.fromisoformat(campaign_data['last_checked'].replace('Z', '+00:00'))
                                    except:
                                        self.campaigns[campaign]['last_checked'] = self.get_ist_time()
                            
                            # Restore datetime objects in completed campaigns
                            for campaign, campaign_data in self.completed_campaigns.items():
                                if 'completed_time' in campaign_data and isinstance(campaign_data['completed_time'], str):
                                    try:
                                        self.completed_campaigns[campaign]['completed_time'] = datetime.fromisoformat(campaign_data['completed_time'].replace('Z', '+00:00'))
                                    except:
                                        self.completed_campaigns[campaign]['completed_time'] = self.get_ist_time()
                            
                            # Restore progress history
                            if 'campaign_progress_history' in data:
                                for campaign, history in data['campaign_progress_history'].items():
                                    self.campaign_progress_history[campaign] = []
                                    for entry in history:
                                        if 'timestamp' in entry and isinstance(entry['timestamp'], str):
                                            try:
                                                entry['timestamp'] = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                                            except:
                                                entry['timestamp'] = self.get_ist_time()
                                        self.campaign_progress_history[campaign].append(entry)
                            
                            # Restore burst patterns datetime objects
                            if 'burst_patterns' in self.learning_data:
                                for campaign, burst_data in self.learning_data['burst_patterns'].items():
                                    if 'burst_times' in burst_data:
                                        restored_times = []
                                        for t in burst_data['burst_times']:
                                            if isinstance(t, str):
                                                try:
                                                    restored_times.append(datetime.fromisoformat(t.replace('Z', '+00:00')))
                                                except:
                                                    restored_times.append(self.get_ist_time())
                                            else:
                                                restored_times.append(t)
                                        self.learning_data['burst_patterns'][campaign]['burst_times'] = restored_times
                                    
                                    if 'first_detection' in burst_data and isinstance(burst_data['first_detection'], str):
                                        try:
                                            self.learning_data['burst_patterns'][campaign]['first_detection'] = datetime.fromisoformat(burst_data['first_detection'].replace('Z', '+00:00'))
                                        except:
                                            self.learning_data['burst_patterns'][campaign]['first_detection'] = self.get_ist_time()
                            
                            logger.info("💾 GIST_LOAD: Bomb predictor data restored!")
                            return True
                logger.info("💾 GIST_LOAD: No existing bomb predictor data found")
                return False
            return False
            
        except Exception as e:
            logger.error(f"GIST_LOAD: Error - {e}")
            return False

    # === LOGIN & SESSION MANAGEMENT ===
    def force_login(self):
        try:
            logger.info("LOGIN: Attempting...")
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
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
                return False
            
            login_data = {'mail': self.email, password_field: self.password}
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            self.human_delay()
            
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            if response.status_code == 200 and "Create New Campaign" in response.text:
                self.session_valid = True
                logger.info("LOGIN: Successful")
                return True
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
            return True
        return self.force_login()

    # === CREDIT MANAGEMENT ===
    def get_visitor_credits(self):
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            visitors_match = re.search(r'Visitors:\s*([\d,]+)', soup.get_text())
            if visitors_match:
                return int(visitors_match.group(1).replace(',', ''))
            return 0
        except:
            return 0

    def get_traffic_credits(self):
        try:
            response = self.session.get("https://adsha.re/exchange/credits/adverts", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            credit_div = soup.find('div', style=re.compile(r'font-size:22pt'))
            if credit_div:
                credit_match = re.search(r'(\d+\.?\d*)', credit_div.get_text().strip())
                if credit_match:
                    return float(credit_match.group(1))
            return 0
        except:
            return 0

    def check_credit_safety(self):
        self.current_traffic_credits = self.get_traffic_credits()
        self.current_visitor_credits = self.get_visitor_credits()
        
        if self.current_traffic_credits >= 1000:
            if self.last_credit_alert != 'convert':
                self.send_telegram(f"💰 CONVERT CREDITS: You have {self.current_traffic_credits} traffic credits - convert to visitors!")
                self.last_credit_alert = 'convert'
        
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

    # === BOMB PREDICTOR INTELLIGENCE ===
    def detect_burst_pattern(self, campaign_name, current_views, current_time):
        """Detect and learn 12-hour burst patterns"""
        try:
            if campaign_name not in self.campaign_progress_history:
                return
            
            history = self.campaign_progress_history[campaign_name]
            if len(history) < 3:
                return
            
            # Calculate recent speed (last 10 minutes)
            recent_views = 0
            recent_minutes = 10
            cutoff_time = current_time - timedelta(minutes=recent_minutes)
            
            for entry in reversed(history):
                if entry['timestamp'] >= cutoff_time:
                    if len(history) > 1 and history[-2]['timestamp'] >= cutoff_time:
                        recent_views += entry['current_views'] - history[-2]['current_views']
                else:
                    break
            
            recent_speed = recent_views / recent_minutes  # views per minute
            
            # Detect burst (unusually high speed)
            normal_speed = self.learning_data['position_speeds'].get('top_speed_avg', 1.0) if self.campaigns.get(campaign_name, {}).get('is_top_position') else self.learning_data['position_speeds'].get('not_top_speed_avg', 0.5)
            
            if recent_speed > normal_speed * 3:  # 3x normal speed = BURST!
                logger.info(f"🚀 BURST_DETECTED: {campaign_name} - {recent_speed:.1f} views/min (normal: {normal_speed:.1f})")
                
                # Initialize burst pattern if not exists
                if campaign_name not in self.learning_data['burst_patterns']:
                    self.learning_data['burst_patterns'][campaign_name] = {
                        'burst_times': [],
                        'burst_sizes': [],
                        'first_detection': current_time
                    }
                
                # Record this burst
                self.learning_data['burst_patterns'][campaign_name]['burst_times'].append(current_time)
                self.learning_data['burst_patterns'][campaign_name]['burst_sizes'].append(recent_views)
                
                # Keep only last 10 bursts
                if len(self.learning_data['burst_patterns'][campaign_name]['burst_times']) > 10:
                    self.learning_data['burst_patterns'][campaign_name]['burst_times'] = self.learning_data['burst_patterns'][campaign_name]['burst_times'][-10:]
                    self.learning_data['burst_patterns'][campaign_name]['burst_sizes'] = self.learning_data['burst_patterns'][campaign_name]['burst_sizes'][-10:]
                
        except Exception as e:
            logger.error(f"BURST_DETECTION: Error - {e}")

    def calculate_burst_aware_prediction(self, campaign_name, current_views, total_views, is_top_position):
        """BOMB PREDICTOR: Burst-aware hybrid prediction"""
        try:
            # Base hybrid prediction
            base_prediction = self.calculate_hybrid_prediction(campaign_name, current_views, total_views, is_top_position)
            
            # Add burst intelligence
            burst_info = self.get_burst_prediction(campaign_name)
            
            if burst_info['burst_expected']:
                remaining_views = total_views - current_views
                burst_eta = burst_info['minutes_to_burst']
                
                if remaining_views <= burst_info['expected_burst_size']:
                    # Burst will complete the campaign!
                    if burst_eta <= 120:  # Within 2 hours
                        return f"🚀 {burst_eta}min (NEXT BURST WILL COMPLETE!)"
                    else:
                        return f"⚡ {base_prediction} + MAJOR BURST IN {burst_eta}min"
                else:
                    return f"⚡ {base_prediction} + BURST IN {burst_eta}min"
            
            return base_prediction
            
        except Exception as e:
            logger.error(f"BURST_PREDICTION: Error - {e}")
            return "Calculating..."

    def calculate_hybrid_prediction(self, campaign_name, current_views, total_views, is_top_position):
        """Original hybrid prediction with multi-window analysis"""
        try:
            if campaign_name not in self.campaign_progress_history:
                return "Collecting data..."
            
            history = self.campaign_progress_history[campaign_name]
            if len(history) < 2:
                return "Collecting data..."
            
            # Multi-window analysis
            short_speed = self.calculate_window_speed(history, 10)
            medium_speed = self.calculate_window_speed(history, 20)
            long_speed = self.calculate_window_speed(history, 30)
            
            # Position-based adjustment
            position_speed = self.learning_data['position_speeds']['top_speed_avg'] if is_top_position else self.learning_data['position_speeds']['not_top_speed_avg']
            
            # Hybrid calculation
            if position_speed > 0:
                valid_speeds = [s for s in [short_speed, medium_speed, long_speed] if s > 0]
                if valid_speeds:
                    real_time_avg = sum(valid_speeds) / len(valid_speeds)
                    final_speed = (real_time_avg * 0.5) + (position_speed * 0.5)
                else:
                    final_speed = position_speed
            else:
                valid_speeds = [s for s in [short_speed, medium_speed, long_speed] if s > 0]
                if valid_speeds:
                    final_speed = sum(valid_speeds) / len(valid_speeds)
                else:
                    return "Stalled"
            
            if final_speed <= 0:
                return "Stalled"
            
            remaining_views = total_views - current_views
            if remaining_views <= 0:
                return "Completed"
            
            minutes_remaining = remaining_views / final_speed
            predicted_end = self.get_ist_time() + timedelta(minutes=minutes_remaining)
            
            if minutes_remaining < 60:
                time_str = f"{int(minutes_remaining)} min"
            else:
                hours = int(minutes_remaining // 60)
                mins = int(minutes_remaining % 60)
                time_str = f"{hours}h {mins}m"
            
            return f"{self.format_ist_time(predicted_end)} IST ({time_str})"
            
        except Exception as e:
            logger.error(f"HYBRID_PREDICTION: Error - {e}")
            return "Error calculating"

    def get_burst_prediction(self, campaign_name):
        """Predict next burst timing and size"""
        try:
            if campaign_name not in self.learning_data['burst_patterns']:
                return {'burst_expected': False}
            
            burst_data = self.learning_data['burst_patterns'][campaign_name]
            burst_times = burst_data['burst_times']
            
            if len(burst_times) < 2:
                return {'burst_expected': False}
            
            # Calculate average time between bursts (should be ~12 hours)
            time_diffs = []
            for i in range(1, len(burst_times)):
                diff = (burst_times[i] - burst_times[i-1]).total_seconds() / 3600  # hours
                time_diffs.append(diff)
            
            avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 12.0
            
            last_burst = burst_times[-1]
            next_expected_burst = last_burst + timedelta(hours=avg_interval)
            minutes_to_burst = (next_expected_burst - self.get_ist_time()).total_seconds() / 60
            
            # Calculate expected burst size
            avg_burst_size = sum(burst_data['burst_sizes']) / len(burst_data['burst_sizes']) if burst_data['burst_sizes'] else 150
            
            return {
                'burst_expected': minutes_to_burst <= 240,  # Within 4 hours
                'minutes_to_burst': int(minutes_to_burst),
                'expected_burst_size': avg_burst_size,
                'confidence': min(len(burst_times) / 10, 1.0)  # More samples = more confidence
            }
            
        except Exception as e:
            logger.error(f"BURST_PREDICTION: Error - {e}")
            return {'burst_expected': False}

    def calculate_window_speed(self, history, window_minutes):
        try:
            window_start = self.get_ist_time() - timedelta(minutes=window_minutes)
            relevant_data = []
            
            for entry in reversed(history):
                if entry['timestamp'] >= window_start:
                    relevant_data.append(entry)
                else:
                    break
            
            if len(relevant_data) < 2:
                return 0
            
            oldest = relevant_data[-1]
            newest = relevant_data[0]
            
            views_gained = newest['current_views'] - oldest['current_views']
            time_diff = (newest['timestamp'] - oldest['timestamp']).total_seconds() / 60
            
            if time_diff <= 0:
                return 0
            
            return views_gained / time_diff
        except:
            return 0

    def update_progress_history(self, campaign_name, current_views, total_views, is_top_position):
        try:
            if campaign_name not in self.campaign_progress_history:
                self.campaign_progress_history[campaign_name] = []
            
            current_time = self.get_ist_time()
            views_per_minute = self.calculate_instant_speed(campaign_name, current_views)
            
            new_entry = {
                'timestamp': current_time,
                'current_views': current_views,
                'total_views': total_views,
                'is_top_position': is_top_position,
                'views_per_minute': views_per_minute,
                'completion_pct': (current_views / total_views * 100) if total_views > 0 else 0
            }
            
            self.campaign_progress_history[campaign_name].append(new_entry)
            if len(self.campaign_progress_history[campaign_name]) > 12:
                self.campaign_progress_history[campaign_name] = self.campaign_progress_history[campaign_name][-12:]
            
            # Update learning data
            if views_per_minute > 0:
                if is_top_position:
                    self.learning_data['position_speeds']['top_speed_samples'].append(views_per_minute)
                    if len(self.learning_data['position_speeds']['top_speed_samples']) > 100:
                        self.learning_data['position_speeds']['top_speed_samples'] = self.learning_data['position_speeds']['top_speed_samples'][-100:]
                    self.learning_data['position_speeds']['top_speed_avg'] = sum(self.learning_data['position_speeds']['top_speed_samples']) / len(self.learning_data['position_speeds']['top_speed_samples'])
                else:
                    self.learning_data['position_speeds']['not_top_speed_samples'].append(views_per_minute)
                    if len(self.learning_data['position_speeds']['not_top_speed_samples']) > 100:
                        self.learning_data['position_speeds']['not_top_speed_samples'] = self.learning_data['position_speeds']['not_top_speed_samples'][-100:]
                    self.learning_data['position_speeds']['not_top_speed_avg'] = sum(self.learning_data['position_speeds']['not_top_speed_samples']) / len(self.learning_data['position_speeds']['not_top_speed_samples'])
            
            # Detect burst patterns
            self.detect_burst_pattern(campaign_name, current_views, current_time)
            
            logger.info(f"📊 PROGRESS_HISTORY: {campaign_name} - {current_views}/{total_views} - {views_per_minute:.2f} views/min")
            
        except Exception as e:
            logger.error(f"PROGRESS_HISTORY: Error - {e}")

    def calculate_instant_speed(self, campaign_name, current_views):
        try:
            if campaign_name not in self.campaign_progress_history:
                return 0
            
            history = self.campaign_progress_history[campaign_name]
            if len(history) < 2:
                return 0
            
            latest = history[-1]
            previous = history[-2]
            
            views_gained = current_views - previous['current_views']
            time_diff = (self.get_ist_time() - previous['timestamp']).total_seconds() / 60
            
            if time_diff <= 0:
                return 0
            
            return views_gained / time_diff
        except:
            return 0

    # === AUTO-BIDDING LOGIC (FROM SECOND SCRIPT) ===
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
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    top_bid_text = soup.get_text()
                    top_bid_match = re.search(r'top bid is (\d+) credits', top_bid_text)
                    
                    if top_bid_match:
                        return int(top_bid_match.group(1))
            return None
        except Exception as e:
            logger.error(f"GET_TOP_BID_ERROR - {e}")
            return None

    def calculate_minimal_bid(self, current_top_bid):
        new_bid = current_top_bid + random.choice(self.minimal_bid_weights)
        
        # Max Bid Limit Alert
        if new_bid > self.max_bid_limit:
            self.send_telegram(f"🛑 MAX BID LIMIT: Would bid {new_bid} but max is {self.max_bid_limit}!")
            return None
        
        return new_bid

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        try:
            if campaign_data['your_bid'] >= current_top_bid:
                return
            
            # Bid Cooldown / Rate Limiting
            current_time = time.time()
            last_bid = self.last_bid_time.get(campaign_name, 0)
            if current_time - last_bid < self.bid_cooldown:
                logger.info(f"RATE_LIMITED - {campaign_name} | Cooldown active")
                return
            
            old_bid = campaign_data['your_bid']
            new_bid = self.calculate_minimal_bid(current_top_bid)
            
            if new_bid is None or new_bid <= old_bid:
                return
            
            # --- Bid Execution Sequence ---
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
            
            if not bid_url: return
            
            response = self.session.get(bid_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'bid'})
            if not form: return
            
            action = form.get('action', '')
            if not action.startswith('http'):
                action = f"https://adsha.re{action}"
            
            bid_data = {'bid': str(new_bid), 'vis': '0'}
            self.human_delay(2, 4)
            
            response = self.session.post(action, data=bid_data, allow_redirects=True)
            
            if response.status_code == 200:
                campaign_data['your_bid'] = new_bid
                self.last_bid_time[campaign_name] = time.time()
                
                logger.info(f"AUTO_BID_SUCCESS - {campaign_name} | {old_bid} → {new_bid} | Regained #1")
                
                # Auto-Bid Success Alert
                success_msg = f"""
🚀 AUTO-BID SUCCESS!

📊 Campaign: <b>{campaign_name}</b>
🎯 Bid: {old_bid} → {new_bid} credits
📈 Increase: +{new_bid - old_bid} credits
🏆 Position: #1 Achieved!
"""
                self.send_telegram(success_msg)
                
        except Exception as e:
            logger.error(f"AUTO_BID_ERROR - {campaign_name} | {e}")

    # === CAMPAIGN PARSING ===
    def parse_campaigns_real_time(self):
        try:
            logger.info("PARSING_REALTIME: Fresh scrape...")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*'))
            logger.info(f"PARSING_REALTIME: Found {len(campaign_divs)} campaigns")
            
            for i, div in enumerate(campaign_divs):
                try:
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
                    
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    your_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    progress_match = re.search(r'(\d+,?\d*)\s*/\s*(\d+,?\d*)\s*visitors', text_content.replace(',', ''))
                    if progress_match:
                        current_views = int(progress_match.group(1).replace(',', ''))
                        total_views = int(progress_match.group(2).replace(',', ''))
                    else:
                        current_views = 0
                        total_views = 0
                    
                    completed = "COMPLETE" in text_content
                    active = "ACTIVE" in text_content
                    
                    is_top_position = your_bid >= self.current_global_bid
                    
                    # Update progress and learning
                    self.update_progress_history(campaign_name, current_views, total_views, is_top_position)
                    
                    # Calculate BURST-AWARE prediction
                    prediction = self.calculate_burst_aware_prediction(campaign_name, current_views, total_views, is_top_position)
                    
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
                        'is_top_position': is_top_position,
                        'status': 'COMPLETED' if completed else 'ACTIVE' if active else 'UNKNOWN',
                        'prediction': prediction,
                        'last_checked': self.get_ist_time()
                    }
                    
                except Exception as e:
                    continue
            
            return campaigns
            
        except Exception as e:
            logger.error(f"PARSING_REALTIME: Error - {e}")
            return {}

    def get_global_top_bid(self):
        try:
            logger.info("BID_CHECK: Getting global top bid...")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            assign_links = soup.find_all('a', href=re.compile(r'/adverts/assign/'))
            
            if not assign_links:
                return 0
            
            first_link = assign_links[0]['href']
            if not first_link.startswith('http'):
                first_link = f"https://adsha.re{first_link}"
            
            response = self.session.get(first_link, timeout=30)
            self.human_delay()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            top_bid_match = re.search(r'top bid is (\d+) credits', page_text)
            if top_bid_match:
                top_bid = int(top_bid_match.group(1))
                logger.info(f"BID_CHECK: Global top bid = {top_bid}")
                return top_bid
            
            return 0
        except Exception as e:
            logger.error(f"BID_CHECK: Error - {e}")
            return 0

    # === TELEGRAM COMMUNICATION ===
    def send_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": message, "parse_mode": 'HTML'}
            response = self.session.post(url, json=data, timeout=30)
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
        elif command_lower == '/extensions':
            self.send_extension_suggestions()
        elif command_lower == '/bursts':
            self.send_burst_analysis()
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
            self.send_telegram("❌ Unknown command. Use /help")

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
        self.send_telegram("💣 BOMB PREDICTOR ACTIVATED!\n\n12-hour burst detection + 1000-2000 visitors/day optimization!")

    def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("MONITORING: Stopped")
        self.send_telegram("🛑 Monitoring STOPPED")

    def send_enhanced_status_real_time(self):
        logger.info("STATUS_REALTIME: Generating...")
        
        if not self.smart_login():
            self.send_telegram("❌ Cannot fetch status - login failed")
            return
        
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
        
        campaigns = self.parse_campaigns_real_time()
        self.campaigns.update(campaigns)
        
        status_msg = f"""
💣 BOMB PREDICTOR - REAL-TIME STATUS

💰 CREDITS:
Traffic: {traffic_credits} | Visitors: {visitor_credits:,}

🎯 GLOBAL TOP BID: {self.current_global_bid} credits

🏆 CAMPAIGN STATUS (BURST-AWARE):
"""
        
        if self.campaigns:
            for name, data in self.campaigns.items():
                is_top = data.get('is_top_position', False)
                status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
                position = "🏆 #1" if is_top else "📉 #2+"
                status_icon = "✅" if data.get('completed') else "🟢" if data.get('active') else "⚪"
                prediction = data.get('prediction', 'Calculating...')
                
                status_msg += f"{position} {status_icon} {name}\n"
                status_msg += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {status}\n"
                status_msg += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
                status_msg += f"   🎯 Predicted End: {prediction}\n\n"
        else:
            status_msg += "No campaigns detected.\n\n"

        # Add burst analysis
        burst_campaigns = [name for name in self.campaigns if name in self.learning_data['burst_patterns']]
        if burst_campaigns:
            status_msg += "🚀 BURST-LEARNING ACTIVE:\n"
            for campaign in burst_campaigns[:2]:
                burst_info = self.get_burst_prediction(campaign)
                if burst_info['burst_expected']:
                    status_msg += f"⚡ {campaign} - Next burst in {burst_info['minutes_to_burst']}min\n"

        status_msg += f"🕒 {current_time} IST | 💣 12-hour burst detection"
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        if not self.campaigns:
            self.send_telegram("📊 No campaigns found.")
            return
        
        campaigns_text = "📋 YOUR CAMPAIGNS (BURST-AWARE)\n\n"
        
        for name, data in self.campaigns.items():
            auto_status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
            position = "🏆 #1" if data.get('is_top_position', False) else "📉 #2+"
            status_icon = "✅ COMPLETED" if data.get('completed') else "🟢 ACTIVE" if data.get('active') else "⚪ UNKNOWN"
            prediction = data.get('prediction', 'Calculating...')
            
            campaigns_text += f"{position} <b>{name}</b>\n"
            campaigns_text += f"   💰 Your Bid: {data['your_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {auto_status}\n"
            campaigns_text += f"   📈 Progress: {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
            campaigns_text += f"   🎯 Predicted End: {prediction}\n"
            campaigns_text += f"   📊 Status: {status_icon}\n\n"
        
        campaigns_text += "💡 Use /auto [campaign] on/off to control auto-bidding"
        self.send_telegram(campaigns_text)

    def send_burst_analysis(self):
        """Show burst pattern analysis"""
        if not self.learning_data['burst_patterns']:
            self.send_telegram("🚀 No burst patterns detected yet. Checking...")
            return
        
        analysis_msg = "🚀 BURST PATTERN ANALYSIS\n\n"
        
        for campaign, data in self.learning_data['burst_patterns'].items():
            burst_info = self.get_burst_prediction(campaign)
            
            analysis_msg += f"<b>{campaign}</b>\n"
            analysis_msg += f"📊 Bursts detected: {len(data['burst_times'])}\n"
            
            if burst_info['burst_expected']:
                analysis_msg += f"🎯 Next burst: {burst_info['minutes_to_burst']} minutes\n"
                analysis_msg += f"📈 Expected size: ~{burst_info['expected_burst_size']} views\n"
                analysis_msg += f"🎲 Confidence: {burst_info['confidence']*100:.0f}%\n"
            else:
                analysis_msg += "⏳ Collecting burst data...\n"
            
            analysis_msg += "\n"
        
        analysis_msg += "💡 Bursts happen every ~12 hours (your revisit timing)"
        self.send_telegram(analysis_msg)

    def send_bid_history(self):
        if not self.bid_history:
            self.send_telegram("📊 No bid history yet.")
            return
        
        filtered_history = []
        last_bid = None
        
        for record in self.bid_history:
            current_bid = record['bid']
            if current_bid != last_bid:
                filtered_history.append(record)
                last_bid = current_bid
        
        if not filtered_history:
            self.send_telegram("📊 No bid changes recorded.")
            return
        
        history_msg = "📈 GLOBAL BID HISTORY (Changes only):\n\n"
        
        for record in filtered_history[-10:]:
            if 'time' in record and isinstance(record['time'], datetime):
                time_str = self.format_ist_time(record['time'])
            else:
                time_str = "Unknown"
            history_msg += f"🕒 {time_str} - {record['bid']} credits\n"
        
        if filtered_history:
            current_bid = filtered_history[-1]['bid']
            if len(filtered_history) >= 2:
                previous_bid = filtered_history[-2]['bid']
                change = current_bid - previous_bid
                change_icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                history_msg += f"\n{change_icon} Current: {current_bid} credits (Change: {change:+d})"
        
        self.send_telegram(history_msg)

    def get_extension_suggestions(self):
        suggestions = []
        visitor_credits = self.get_visitor_credits()
        
        for campaign_name, data in self.campaigns.items():
            if data.get('completed') and campaign_name not in self.completed_campaigns:
                # BURST-AWARE extension timing
                burst_info = self.get_burst_prediction(campaign_name)
                suggested_views = min(500, visitor_credits)
                
                suggestion = {
                    'campaign': campaign_name,
                    'suggested_views': suggested_views,
                    'credits_needed': suggested_views,
                    'current_bid': data.get('your_bid', 0)
                }
                
                # Add burst timing advice
                if burst_info['burst_expected']:
                    if burst_info['minutes_to_burst'] < 60:
                        suggestion['advice'] = f"WAIT {burst_info['minutes_to_burst']}min - Extend after next burst"
                    else:
                        suggestion['advice'] = "EXTEND NOW - Catch current cycle"
                else:
                    suggestion['advice'] = "EXTEND NOW - Normal timing"
                
                suggestions.append(suggestion)
        
        return suggestions

    def send_extension_suggestions(self):
        suggestions = self.get_extension_suggestions()
        
        if not suggestions:
            self.send_telegram("✅ No completed campaigns needing extension.")
            return
        
        extensions_text = "💡 BURST-AWARE EXTENSION SUGGESTIONS\n\n"
        
        for suggestion in suggestions:
            extensions_text += f"✅ <b>{suggestion['campaign']}</b>\n"
            extensions_text += f"   📊 Add: {suggestion['suggested_views']} views\n"
            extensions_text += f"   💰 Cost: {suggestion['credits_needed']} credits\n"
            extensions_text += f"   🎯 Strategy: {suggestion.get('advice', 'Normal extension')}\n\n"
        
        visitor_credits = self.get_visitor_credits()
        extensions_text += f"💰 Your credits: {visitor_credits:,} visitors available\n"
        extensions_text += "🚀 Maximizing unique viewers in 24h with burst timing!"
        
        self.send_telegram(extensions_text)

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
💣 BOMB PREDICTOR - COMMANDS:

/start - Start 24/7 monitoring
/stop - Stop monitoring
/status - Real-time status with burst predictions
/campaigns - List all campaigns with ETAs
/bids - Clean bid history (changes only)
/extensions - Completed campaigns with burst timing
/bursts - Burst pattern analysis
/target [amount] - Set max bid limit
/autobid on/off - Auto-bid for all campaigns
/auto [campaign] on/off - Auto-bid for specific campaign

🎯 BOMB PREDICTOR FEATURES:
• 12-hour burst detection & prediction
• "NEXT BURST WILL COMPLETE!" alerts
• Burst-aware extension timing
• 1000-2000 visitors/day optimization
• Maximum unique viewers strategy
• GitHub learning persistence
• ACTIVE AUTO-BIDDING with rate limiting
"""
        self.send_telegram(help_msg)

    def check_completion_alerts(self):
        try:
            for campaign_name, campaign_data in self.campaigns.items():
                completion_pct = campaign_data.get('completion_pct', 0)
                
                # 99% completion alert with BURST AWARENESS
                if 99.0 <= completion_pct < 100.0:
                    alert_key = f"99pct_{campaign_name}"
                    if alert_key not in self.sent_alerts:
                        burst_info = self.get_burst_prediction(campaign_name)
                        
                        if burst_info['burst_expected'] and burst_info['minutes_to_burst'] < 120:
                            # Burst coming soon - recommend WAIT
                            message = f"""
🚨 CAMPAIGN AT 99% - BURST STRATEGY!

"{campaign_name}"
📈 Progress: {campaign_data['progress']} ({completion_pct:.1f}%)
Remaining: {campaign_data['total_views'] - campaign_data['current_views']} views

🎯 BURST PREDICTION:
Next 12-hour cycle in: {burst_info['minutes_to_burst']} minutes
Expected burst: ~{burst_info['expected_burst_size']} views

💡 RECOMMENDATION: WAIT {burst_info['minutes_to_burst']} MINUTES
- Will complete naturally in next burst
- Save credits for optimal extension
- Maximum unique viewers strategy ✅
"""
                        else:
                            # Normal 99% alert
                            message = f"""
🚨 CAMPAIGN NEARING COMPLETION!

"{campaign_name}"
📈 Progress: {campaign_data['progress']} ({completion_pct:.1f}%)

⏰ EXTEND SOON - Will complete shortly!
"""
                        
                        self.send_telegram(message)
                        self.sent_alerts[alert_key] = True
                        logger.info(f"COMPLETION_ALERT: 99% alert for {campaign_name}")
                
                # 100% completion alert with extension suggestion
                if completion_pct >= 99.9 and campaign_data.get('completed'):
                    alert_key = f"completed_{campaign_name}"
                    if alert_key not in self.sent_alerts:
                        visitor_credits = self.get_visitor_credits()
                        suggested_views = min(500, visitor_credits)
                        
                        # Burst-aware extension timing
                        burst_info = self.get_burst_prediction(campaign_name)
                        timing_advice = ""
                        if burst_info['burst_expected']:
                            if burst_info['minutes_to_burst'] < 60:
                                timing_advice = f"⏰ Next burst in {burst_info['minutes_to_burst']}min - Perfect timing!"
                            else:
                                timing_advice = f"🔄 Next burst in {burst_info['minutes_to_burst']}min - Extend now!"
                        
                        message = f"""
✅ CAMPAIGN COMPLETED - BURST TIMING!

"{campaign_name}"
📊 Final: {campaign_data['progress']} (100%)

💡 SMART EXTENSION STRATEGY:
Add {suggested_views} views using {suggested_views} credits
{timing_advice}

💰 Your credits: {visitor_credits:,} visitors available
🎯 Goal: Maximum unique viewers in 24h
🚀 Action: Go to adsha.re → Find campaign → Add views
"""
                        self.send_telegram(message)
                        self.sent_alerts[alert_key] = True
                        self.completed_campaigns[campaign_name] = {
                            'completed_time': self.get_ist_time(),
                            'total_views': campaign_data['total_views'],
                            'your_bid': campaign_data['your_bid']
                        }
                        logger.info(f"COMPLETION_ALERT: 100% alert for {campaign_name}")
                        
        except Exception as e:
            logger.error(f"COMPLETION_ALERT: Error - {e}")

    def send_hourly_status(self):
        if not self.campaigns:
            return
            
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        current_time = self.format_ist_time()
        
        status_msg = f"""
🕐 HOURLY STATUS - BOMB PREDICTOR
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
                    position = "🏆 #1" if data.get('is_top_position', False) else "📉 #2+"
                    status_icon = "✅" if data.get('completed') else "🟢"
                    prediction = data.get('prediction', 'Calculating...')
                    status_msg += f"{position} {status_icon} \"{name}\" - {data['progress']} ({data.get('completion_pct', 0):.1f}%)\n"
                    status_msg += f"   🎯 ETA: {prediction}\n"
        
        # Add burst learning progress
        burst_campaigns = len(self.learning_data['burst_patterns'])
        total_bursts = sum(len(data['burst_times']) for data in self.learning_data['burst_patterns'].values())
        
        status_msg += f"\n🚀 BURST LEARNING: {burst_campaigns} campaigns, {total_bursts} bursts tracked"
        status_msg += "\n\n💣 12-hour cycle optimization active..."
        
        self.send_telegram(status_msg)
        logger.info("HOURLY_STATUS: Sent bomb predictor report")

    def check_bid_drop(self, new_bid):
        if len(self.bid_history) < 2:
            return False, 0
        
        previous_bid = self.bid_history[-1]['bid']
        if new_bid < previous_bid - 50:
            drop_amount = previous_bid - new_bid
            logger.info(f"BID_ALERT: Drop {previous_bid}→{new_bid} (-{drop_amount})")
            return True, drop_amount
        
        return False, 0

    def check_and_alert(self):
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("MONITORING: Login failed")
            return
        
        # Get global top bid
        global_top_bid = self.get_global_top_bid()
        
        if global_top_bid > 0:
            # Only record bid if changed
            if not self.bid_history or self.bid_history[-1]['bid'] != global_top_bid:
                self.bid_history.append({
                    'bid': global_top_bid,
                    'time': self.get_ist_time(),
                    'type': 'global'
                })
                logger.info(f"💰 BID_UPDATE: Changed to {global_top_bid} credits")
            
            if len(self.bid_history) > 100:
                self.bid_history = self.bid_history[-100:]
            
            self.current_global_bid = global_top_bid
            
            # Check for bid drops
            if len(self.bid_history) >= 2:
                drop_detected, drop_amount = self.check_bid_drop(global_top_bid)
                if drop_detected:
                    current_time = time.time()
                    if current_time - self.last_alert_time > 3600:
                        previous_bid = self.bid_history[-2]['bid']
                        alert_msg = f"""
📉 BID DROP OPPORTUNITY!

Global top bid dropped from {previous_bid} → {global_top_bid} credits
💰 SAVE {drop_amount} CREDITS!

Perfect time to start new campaign!
"""
                        self.send_telegram(alert_msg)
                        self.last_alert_time = current_time
                        logger.info(f"BID_ALERT: Drop alert sent")
        
        # Parse campaigns with BURST-AWARE predictions
        new_campaigns = self.parse_campaigns_real_time()
        for campaign_name in new_campaigns:
            new_campaigns[campaign_name]['top_bid'] = self.current_global_bid
        self.campaigns.update(new_campaigns)
        
        # Execute AUTO-BIDDING for campaigns with auto-bid enabled
        credit_safe = self.check_credit_safety()
        if credit_safe and (self.auto_bid_enabled or any(campaign.get('auto_bid', False) for campaign in self.campaigns.values())):
            for campaign_name, campaign_data in self.campaigns.items():
                if campaign_data.get('auto_bid', False) or self.auto_bid_enabled:
                    # Get actual top bid for this campaign
                    actual_top_bid = self.get_top_bid_from_bid_page(campaign_name)
                    if actual_top_bid and actual_top_bid > campaign_data['your_bid']:
                        self.execute_smart_auto_bid(campaign_name, campaign_data, actual_top_bid)
        
        # Check completion alerts with burst awareness
        self.check_completion_alerts()
        
        # Auto-save every hour
        if time.time() - self.last_save_time > 3600:
            self.save_to_github()

    def run(self):
        logger.info("💣 Starting Ultimate Bomb Predictor...")
        
        if not self.force_login():
            logger.error("❌ Failed to start - login failed")
            return
        
        if not hasattr(self, 'sent_alerts'):
            self.sent_alerts = {}
        
        startup_msg = "💣 BOMB PREDICTOR STARTED!\n• 12-hour burst detection\n• 1000-2000 visitors/day optimization\n• Maximum unique viewers strategy\n• Burst-aware predictions\n• ACTIVE AUTO-BIDDING with rate limiting\nType /help for commands"
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
                    logger.info("🔍 Performing scheduled check...")
                    self.check_and_alert()
                    last_check = current_time
                    logger.info("✅ Check completed")
                
                # Hourly status report
                if self.is_monitoring and current_time - last_hourly_status >= 3600:
                    logger.info("🕐 Sending hourly status...")
                    self.send_hourly_status()
                    last_hourly_status = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = UltimateBidder()
    bot.run()
