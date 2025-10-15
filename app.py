import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime
from flask import Flask
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 AdShare Auto-Bid Bot Running - Background Process Active"

@app.route('/health')
def health():
    return "✅ Bot Healthy - Monitoring Active"

class AdShareStealthBot:
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
        self.last_action_time = 0
        self.action_count_today = 0
        
        # Bot settings
        self.is_monitoring = False
        self.base_check_interval = 600
        
        # Auto-bid settings
        self.campaigns = {}
        self.default_max_bid = 180
        
        # Safety settings
        self.daily_action_limit = 50
        self.min_delay_between_actions = 2
        self.max_delay_between_actions = 8
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'last_auto_bid': None,
            'safety_skips': 0
        }

    def rotate_user_agent(self):
        """Rotate user agents"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        ]
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
        })

    def human_delay(self, min_seconds=None, max_seconds=None):
        """Random delay between actions"""
        min_delay = min_seconds or self.min_delay_between_actions
        max_delay = max_seconds or self.max_delay_between_actions
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        return delay

    def get_random_check_interval(self):
        """Random check interval between 8-15 minutes"""
        return random.randint(480, 900)

    def calculate_smart_bid(self, current_top_bid, my_bid, campaign_name):
        """Smart bidding strategy"""
        weights = [1, 2, 2, 2, 3, 3, 4]
        base_increment = random.choice(weights)
        
        if random.random() < 0.1:
            base_increment += random.randint(2, 4)
        
        new_bid = current_top_bid + base_increment
        campaign_max = self.campaigns[campaign_name].get('max_bid', self.default_max_bid)
        return min(new_bid, campaign_max)

    def should_skip_action(self, action_type="check"):
        """Safety check"""
        current_hour = datetime.now().hour
        if current_hour == 0 and self.action_count_today > 0:
            self.action_count_today = 0
        
        if self.action_count_today >= self.daily_action_limit:
            return True
        
        skip_chance = 0.15 if action_type == "bid" else 0.05
        if random.random() < skip_chance:
            self.stats['safety_skips'] += 1
            return True
        
        time_since_last = time.time() - self.last_action_time
        if time_since_last < self.min_delay_between_actions:
            return True
        
        return False

    def smart_login(self):
        """Ultra-safe login"""
        if self.check_session_valid():
            self.session_valid = True
            return True
        
        self.human_delay(3, 7)
        return self.force_login()

    def check_session_valid(self):
        """Lightweight session check"""
        try:
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            if response.status_code == 302 and "login" in response.headers.get('Location', ''):
                self.session_valid = False
                return False
            self.session_valid = True
            return True
        except Exception as e:
            self.session_valid = False
            return False

    def force_login(self):
        """Safe login"""
        try:
            logger.info("🔄 Performing safe login...")
            self.human_delay(2, 5)
            
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay(1, 3)
            
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
            self.human_delay(2, 4)
            
            if self.check_session_valid():
                self.session_valid = True
                self.stats['logins_made'] += 1
                self.consecutive_failures = 0
                logger.info(f"✅ Login successful")
                return True
            else:
                self.consecutive_failures += 1
                return False
                
        except Exception as e:
            self.consecutive_failures += 1
            return False

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
            return False

    def process_telegram_command(self):
        """Process commands without duplicates"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 5
            }
            
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
                                logger.info(f"📨 Processing: {text}")
                                self.handle_command(text, chat_id)
                            
        except Exception as e:
            pass

    def handle_command(self, command, chat_id):
        """Handle commands"""
        command_lower = command.lower().strip()
        
        if command_lower == '/start':
            self.start_monitoring()
        elif command_lower == '/stop':
            self.stop_monitoring()
        elif command_lower == '/status':
            self.send_status()
        elif command_lower.startswith('/auto'):
            self.handle_auto_command(command)
        elif command_lower == '/campaigns':
            self.send_campaigns_list()
        elif command_lower == '/help':
            self.send_help()
        else:
            self.send_telegram("❌ Unknown command. Use /help")

    def handle_auto_command(self, command):
        """Case-insensitive campaign matching"""
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
                    else:
                        self.send_telegram("❌ Use: /auto \"Campaign Name\" on")
                        return
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
        logger.info("🚀 Stealth monitoring started")
        self.send_telegram("🚀 Bot Activated! Monitoring started.")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
        self.send_telegram("🛑 Bot Stopped!")

    def send_status(self):
        """Send status"""
        if not self.campaigns:
            status_msg = "📊 Bot Status: Inactive - Send /start"
        else:
            campaigns_list = ""
            for name, data in self.campaigns.items():
                status = "✅" if data.get('auto_bid', False) else "❌"
                campaigns_list += f"📊 {name}: {data['my_bid']} credits (Auto: {status})\n"
            
            status_msg = f"""
📊 Bot Status

Monitoring: {'✅ Active' if self.is_monitoring else '❌ Inactive'}
Campaigns:
{campaigns_list}
Checks: {self.stats['checks_made']}
Auto Bids: {self.stats['auto_bids_made']}
            """
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        """Show campaigns"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
            
        campaigns_msg = "📊 Your Campaigns:\n\n"
        for name, data in self.campaigns.items():
            auto_status = "✅ ON" if data.get('auto_bid', False) else "❌ OFF"
            campaigns_msg += f"<b>{name}</b>\n"
            campaigns_msg += f"Bid: {data['my_bid']} credits\n"
            campaigns_msg += f"Auto: {auto_status}\n"
            campaigns_msg += f"<code>/auto \"{name}\" on</code>\n\n"
        
        self.send_telegram(campaigns_msg)

    def send_help(self):
        """Send help"""
        help_msg = """
🤖 Auto-Bid Bot

/start - Start monitoring
/stop - Stop monitoring  
/status - Status
/campaigns - List campaigns

/auto all on - Enable all
/auto "My Advert" on - Enable specific
        """
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        """Extract campaign data preserving auto_bid"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            new_campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                text_content = div.get_text().strip()
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if lines:
                    first_line = lines[0]
                    
                    if 'http' in first_line:
                        campaign_name = first_line.split('http')[0].strip()
                    elif 'www.' in first_line:
                        campaign_name = first_line.split('www.')[0].strip()
                    else:
                        campaign_name = first_line
                    
                    campaign_name = campaign_name.rstrip('.:- ')
                    
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    my_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    if campaign_name and my_bid > 0:
                        auto_bid = False
                        if campaign_name in self.campaigns:
                            auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                        
                        new_campaigns[campaign_name] = {
                            'my_bid': my_bid,
                            'top_bid': my_bid,
                            'auto_bid': auto_bid,
                            'max_bid': self.default_max_bid,
                            'last_checked': None
                        }
            
            return new_campaigns
            
        except Exception as e:
            return {}

    def get_top_bid_from_bid_page(self, campaign_name):
        """Get top bid from bid page"""
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 3)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            increase_links = soup.find_all('a', href=re.compile(r'/adverts/bid/'))
            
            for link in increase_links:
                campaign_div = link.find_parent('div', style=re.compile(r'border.*solid.*#8CC63F'))
                if campaign_div and campaign_name in campaign_div.get_text():
                    bid_url = link['href']
                    if not bid_url.startswith('http'):
                        bid_url = f"https://adsha.re{bid_url}"
                    
                    response = self.session.get(bid_url, timeout=30)
                    self.human_delay(1, 3)
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    top_bid_text = soup.find(string=re.compile(r'top bid is \d+ credits'))
                    
                    if top_bid_text:
                        match = re.search(r'top bid is (\d+) credits', top_bid_text)
                        if match:
                            return int(match.group(1))
            
            return None
            
        except Exception as e:
            return None

    def check_all_campaigns(self):
        """Check campaigns preserving auto-bid settings"""
        if not self.is_monitoring:
            return
            
        if self.should_skip_action("check"):
            return
            
        self.stats['checks_made'] += 1
        self.action_count_today += 1
        self.last_action_time = time.time()
        
        if not self.smart_login():
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 3)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    self.campaigns[campaign_name]['my_bid'] = new_data['my_bid']
                    self.campaigns[campaign_name]['top_bid'] = new_data['top_bid']
                else:
                    self.campaigns[campaign_name] = new_data
            
            if not self.campaigns:
                return
            
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now().strftime('%H:%M:%S')
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}, Auto: {campaign_data['auto_bid']}")
                    
                    if (campaign_data['auto_bid'] and 
                        top_bid > campaign_data['my_bid'] and 
                        not self.should_skip_action("bid")):
                        
                        self.execute_safe_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            pass

    def execute_safe_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        """Execute auto-bid"""
        try:
            new_bid = self.calculate_smart_bid(current_top_bid, campaign_data['my_bid'], campaign_name)
            
            if new_bid > campaign_data['max_bid']:
                return
            
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 3)
            
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
            self.human_delay(1, 3)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'bid'})
            
            if not form:
                return
            
            action = form.get('action', '')
            if not action.startswith('http'):
                action = f"https://adsha.re{action}"
            
            bid_data = {'bid': str(new_bid), 'vis': '0'}
            self.human_delay(2, 5)
            
            response = self.session.post(action, data=bid_data, allow_redirects=True)
            
            if response.status_code == 200:
                self.stats['auto_bids_made'] += 1
                self.action_count_today += 1
                self.stats['last_auto_bid'] = datetime.now().strftime('%H:%M:%S')
                campaign_data['my_bid'] = new_bid
                
                logger.info(f"🚀 AUTO-BID: {campaign_name} → {new_bid}")
                
                success_msg = f"""
🚀 AUTO-BID SUCCESS!

📊 Campaign: {campaign_name}
🎯 Bid: {campaign_data['my_bid']} → {new_bid} credits

✅ Now at #1 position!
                """
                self.send_telegram(success_msg)
                
        except Exception as e:
            pass

    def run(self):
        """Main bot loop"""
        logger.info("🤖 Starting Bot...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🛡️ Bot Activated! Use /start")
        
        last_command_check = 0
        last_campaign_check = 0
        next_check_interval = self.get_random_check_interval()
        
        while True:
            try:
                current_time = time.time()
                
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                if (self.is_monitoring and 
                    current_time - last_campaign_check >= next_check_interval):
                    
                    self.check_all_campaigns()
                    last_campaign_check = current_time
                    next_check_interval = self.get_random_check_interval()
                
                time.sleep(1)
                
            except Exception as e:
                time.sleep(30)

def run_bot():
    """Run the bot in a separate thread"""
    bot = AdShareStealthBot()
    bot.run()

if __name__ == "__main__":
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask web server (for Render port)
    app.run(host='0.0.0.0', port=10000, debug=False)
