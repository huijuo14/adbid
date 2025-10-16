import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime, timedelta
from flask import Flask
import threading
import pickle
import os
import socket
import sys

# Instance locking
def check_port_in_use(port=10001):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            return False
    except OSError:
        return True

for i in range(5):
    if check_port_in_use():
        if i == 4:
            print("❌ Another instance is running! Exiting...")
            sys.exit(1)
        time.sleep(2)
    else:
        break

print("✅ Instance check passed - starting bot...")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

app = Flask(__name__)

class UltimateSmartBidder:
    def __init__(self):
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.last_update_id = 0
        self.email = "loginallapps@gmail.com"
        self.password = "@Sd2007123"
        
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        self.is_monitoring = False
        self.campaigns = {}
        
        self.minimal_bid_weights = [1, 2]  # Only +1 or +2 credits
        self.check_interval = 300  # Fixed 5-minute checks
        
        self.visitor_alert_threshold = 1000
        self.visitor_stop_threshold = 500
        self.current_traffic_credits = 0
        self.current_visitor_credits = 0
        self.last_credit_alert = None
        
        # Alert tracking
        self.sent_alerts = {}
        
        self.load_bot_state()
        self.get_render_ip()

    def save_bot_state(self):
        try:
            state_data = {
                'campaigns': self.campaigns,
                'last_update_id': self.last_update_id,
                'session_valid': self.session_valid,
                'is_monitoring': self.is_monitoring,
                'sent_alerts': self.sent_alerts
            }
            with open('bot_state.pkl', 'wb') as f:
                pickle.dump(state_data, f)
        except Exception as e:
            logger.error(f"Save state error: {e}")

    def load_bot_state(self):
        try:
            if os.path.exists('bot_state.pkl'):
                with open('bot_state.pkl', 'rb') as f:
                    state_data = pickle.load(f)
                    self.campaigns = state_data.get('campaigns', {})
                    self.last_update_id = state_data.get('last_update_id', 0)
                    self.session_valid = state_data.get('session_valid', False)
                    self.is_monitoring = state_data.get('is_monitoring', False)
                    self.sent_alerts = state_data.get('sent_alerts', {})
                logger.info("📂 Bot state loaded")
        except Exception as e:
            logger.error(f"Load state error: {e}")

    def rotate_user_agent(self):
        user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def get_render_ip(self):
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
        self.current_traffic_credits = self.get_traffic_credits()
        self.current_visitor_credits = self.get_visitor_credits()
        
        # Credit conversion reminder
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

        status_msg = f"""
📊 SMART STATUS

💰 CREDITS: Traffic {traffic_credits} | Visitors {visitor_credits:,}

🏆 POSITION: {top_campaigns}/{total_campaigns} at #1

{campaigns_list}
"""
        self.send_telegram(status_msg)

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

/start - Start monitoring
/stop - Stop monitoring  
/status - Credits & campaigns
/campaigns - List campaigns
/auto [campaign] on/off - Toggle auto-bid

💡 SMART FEATURES:
• +1-2 credit bidding
• Campaign completion alerts
• Credit protection
• Credit conversion reminders
"""
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            new_campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
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
                my_bid = int(bid_match.group(1)) if bid_match else 0
                
                views_match = re.search(r'(\d+)\s*/\s*(\d+)\s*visitors', text_content)
                hits_match = re.search(r'(\d+)\s*hits', text_content)
                
                current_views = int(views_match.group(1)) if views_match else 0
                total_views = int(views_match.group(2)) if views_match else 0
                total_hits = int(hits_match.group(1)) if hits_match else 0
                
                if campaign_name and my_bid > 0:
                    auto_bid = False
                    if campaign_name in self.campaigns:
                        auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                    
                    new_campaigns[campaign_name] = {
                        'my_bid': my_bid,
                        'top_bid': my_bid,
                        'auto_bid': auto_bid,
                        'last_bid_time': None,
                        'last_checked': None,
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

    def check_completion_alerts(self, campaign_name, campaign_data):
        if 'views' not in campaign_data:
            return
            
        current = campaign_data['views']['current']
        total = campaign_data['views']['total']
        
        if total == 0:
            return
            
        completion_ratio = current / total
        alert_key = f"{campaign_name}_{int(completion_ratio * 100)}"
        
        # 50% alert
        if completion_ratio >= 0.5 and completion_ratio < 0.75:
            if alert_key not in self.sent_alerts:
                self.send_telegram(f"📊 Campaign Progress:\n\"{campaign_name}\" - {current:,}/{total:,} views (50%)\n✅ Halfway there!")
                self.sent_alerts[alert_key] = True
        
        # 75% alert  
        elif completion_ratio >= 0.75 and completion_ratio < 0.98:
            if alert_key not in self.sent_alerts:
                self.send_telegram(f"📊 Campaign Progress:\n\"{campaign_name}\" - {current:,}/{total:,} views (75%)\n⚠️ Almost done!")
                self.sent_alerts[alert_key] = True
        
        # 98% alert
        elif completion_ratio >= 0.98 and completion_ratio < 1.0:
            if alert_key not in self.sent_alerts:
                self.send_telegram(f"📊 Campaign Progress:\n\"{campaign_name}\" - {current:,}/{total:,} views (98%)\n🎯 Virtually complete - Ready to extend soon!")
                self.sent_alerts[alert_key] = True
        
        # 100% alert
        elif completion_ratio >= 1.0:
            if alert_key not in self.sent_alerts:
                self.send_telegram(f"✅ Campaign Completed:\n\"{campaign_name}\" - {current:,}/{total:,} views (100%)\n🚨 EXTEND NOW - Bid reset to 0!")
                self.sent_alerts[alert_key] = True

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        try:
            if campaign_data['my_bid'] >= current_top_bid:
                return
            
            old_bid = campaign_data['my_bid']
            new_bid = self.calculate_minimal_bid(current_top_bid)
            
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
                campaign_data['my_bid'] = new_bid
                campaign_data['last_bid_time'] = datetime.now()
                
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
        
        if not self.smart_login():
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                    self.campaigns[campaign_name].update(new_data)
                    self.campaigns[campaign_name]['auto_bid'] = auto_bid
                else:
                    self.campaigns[campaign_name] = new_data
            
            if not self.campaigns:
                return
            
            credit_safe = self.check_credit_safety()
            
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    old_top_bid = campaign_data.get('top_bid', 0)
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now()
                    
                    # Check for bid changes alert
if old_top_bid > 0:
    if top_bid < old_top_bid:
        self.send_telegram(f"🔔 BID DECREASE:\n\"{campaign_name}\" - Top bid dropped from {old_top_bid} to {top_bid}!")
    elif top_bid > old_top_bid:
        self.send_telegram(f"📈 BID INCREASE:\n\"{campaign_name}\" - Top bid rose from {old_top_bid} to {top_bid}!")
        
                    # Check completion alerts
                    self.check_completion_alerts(campaign_name, campaign_data)
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}")
                    
                    if credit_safe and campaign_data['auto_bid']:
                        self.execute_smart_auto_bid(campaign_name, campaign_data, top_bid)
                        
            self.save_bot_state()
                        
        except Exception as e:
            logger.error(f"Check error: {e}")

    def run(self):
        logger.info("🤖 Starting Ultimate Smart Bidder...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🚀 Ultimate Smart Bidder Activated!")
        
        last_command_check = 0
        last_campaign_check = 0
        last_save_time = time.time()
        
        while True:
            try:
                current_time = time.time()
                
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                if current_time - last_save_time >= 300:
                    self.save_bot_state()
                    last_save_time = current_time
                
                if self.is_monitoring:
                    if current_time - last_campaign_check >= self.check_interval:
                        self.check_all_campaigns()
                        last_campaign_check = current_time
                        logger.info(f"🔄 Check complete. Next in {self.check_interval//60}min")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)

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
    app.bot_instance = bot
    bot.run()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    app.run(host='0.0.0.0', port=10001, debug=False)
