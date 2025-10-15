import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class AdShareStealthBot:
    def __init__(self):
        # Telegram credentials
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.last_update_id = 0  # Track last processed message
        
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
        self.base_check_interval = 600  # 10 minutes base
        
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
        """Rotate user agents to appear more human"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
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
            logger.info(f"🎯 Strategic overbid for {campaign_name}")
        
        new_bid = current_top_bid + base_increment
        campaign_max = self.campaigns[campaign_name].get('max_bid', self.default_max_bid)
        return min(new_bid, campaign_max)

    def should_skip_action(self, action_type="check"):
        """Safety check - skip action if needed"""
        current_hour = datetime.now().hour
        if current_hour == 0 and self.action_count_today > 0:
            self.action_count_today = 0
            logger.info("🔄 Daily action counter reset")
        
        if self.action_count_today >= self.daily_action_limit:
            logger.warning(f"⏹️ Daily action limit reached ({self.daily_action_limit})")
            return True
        
        skip_chance = 0.15 if action_type == "bid" else 0.05
        if random.random() < skip_chance:
            self.stats['safety_skips'] += 1
            logger.info(f"🎯 Safety skip: {action_type}")
            return True
        
        time_since_last = time.time() - self.last_action_time
        if time_since_last < self.min_delay_between_actions:
            return True
        
        return False

    def occasional_long_break(self):
        """Take occasional long breaks"""
        if random.random() < 0.03:
            break_minutes = random.randint(30, 240)
            logger.info(f"😴 Taking human-like break: {break_minutes} minutes")
            self.send_telegram(f"😴 <b>Taking a break</b>\nBack in {break_minutes} minutes")
            time.sleep(break_minutes * 60)
            return True
        return False

    def smart_login(self):
        """Ultra-safe login"""
        if self.check_session_valid():
            self.session_valid = True
            logger.info("✅ Session valid, reusing")
            return True
        
        self.human_delay(3, 7)
        logger.info("🔐 Session expired, performing fresh login")
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
            logger.error(f"Session check error: {e}")
            self.session_valid = False
            return False

    def force_login(self):
        """Safe login"""
        try:
            logger.info("🔄 Performing safe login...")
            self.human_delay(2, 5)
            
            if random.random() < 0.3:
                self.rotate_user_agent()
            
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
                logger.info(f"✅ Login successful (Total logins: {self.stats['logins_made']})")
                return True
            else:
                self.consecutive_failures += 1
                logger.error(f"❌ Login failed")
                return False
                
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Login error: {e}")
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
            logger.error(f"Telegram error: {e}")
            return False

    def process_telegram_command(self):
        """FIXED: Process commands without duplicates"""
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
                    
                    # CRITICAL FIX: Only process NEW updates
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
            logger.error(f"Command processing error: {e}")

    def handle_command(self, command, chat_id):
        """Handle commands - NO DUPLICATES"""
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
            
        elif command_lower == '/safety':
            self.send_safety_status()
            
        elif command_lower == '/help':
            self.send_help()
            
        else:
            self.send_telegram("❌ Unknown command. Use /help for available commands.")

    def handle_auto_command(self, command):
        """FIXED: Case-insensitive campaign matching"""
        parts = command.split()
        
        if len(parts) == 1:
            self.send_telegram("❌ Usage: /auto [campaign] on/off\nExample: /auto \"My Advert\" on")
            return
            
        if len(parts) == 2 and parts[1].lower() in ['on', 'off']:
            action = parts[1].lower()
            for campaign_name in self.campaigns:
                self.campaigns[campaign_name]['auto_bid'] = (action == 'on')
            
            status = "enabled" if action == 'on' else "disabled"
            self.send_telegram(f"🔄 <b>Auto-bid {status} for all campaigns</b>")
            return
            
        if len(parts) >= 3:
            # Extract campaign name (handle quoted names)
            if command.count('"') >= 2:
                # Handle quoted campaign names like: /auto "My Advert" on
                import shlex
                try:
                    parsed = shlex.split(command)
                    if len(parsed) >= 3:
                        campaign_name = parsed[1]
                        action = parsed[2].lower()
                    else:
                        self.send_telegram("❌ Invalid format. Use: /auto \"Campaign Name\" on")
                        return
                except:
                    campaign_name = ' '.join(parts[1:-1])
                    action = parts[-1].lower()
            else:
                campaign_name = ' '.join(parts[1:-1])
                action = parts[-1].lower()
            
            if action not in ['on', 'off']:
                self.send_telegram("❌ Action must be 'on' or 'off'")
                return
            
            # FIXED: Case-insensitive matching
            found_campaign = None
            for stored_name in self.campaigns.keys():
                if stored_name.lower() == campaign_name.lower():
                    found_campaign = stored_name
                    break
            
            if found_campaign:
                self.campaigns[found_campaign]['auto_bid'] = (action == 'on')
                status = "enabled" if action == 'on' else "disabled"
                self.send_telegram(f"🔄 <b>Auto-bid {status} for '{found_campaign}'</b>")
                
                # Update the stored name to match exactly what user typed (for consistency)
                if found_campaign != campaign_name:
                    self.campaigns[campaign_name] = self.campaigns.pop(found_campaign)
            else:
                available = list(self.campaigns.keys())
                if available:
                    available_str = "\n".join([f"• {name}" for name in available])
                    self.send_telegram(f"❌ Campaign '{campaign_name}' not found.\n\nAvailable campaigns:\n{available_str}")
                else:
                    self.send_telegram("❌ No campaigns found. Send /start to load campaigns.")

    def start_monitoring(self):
        """Start monitoring"""
        self.is_monitoring = True
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("🚀 Stealth monitoring started")
        self.send_telegram("🚀 <b>Stealth Bot Activated!</b>\nMonitoring started with anti-detection features.")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
        self.send_telegram("🛑 <b>Stealth Bot Stopped!</b>")

    def send_status(self):
        """Send status"""
        if not self.campaigns:
            status_msg = """
📊 <b>Stealth Bot Status</b>

🔄 <b>Monitoring:</b> ❌ Inactive
🛡️ <b>Safety Mode:</b> ✅ Ultra-Safe

💡 <b>Send /start to begin monitoring</b>
            """
        else:
            campaigns_list = ""
            for name, data in self.campaigns.items():
                status = "✅" if data.get('auto_bid', False) else "❌"
                campaigns_list += f"📊 {name}: {data['my_bid']} credits (Auto: {status})\n"
            
            status_msg = f"""
📊 <b>Stealth Bot Status</b>

🔄 <b>Monitoring:</b> {'✅ Active' if self.is_monitoring else '❌ Inactive'}
🛡️ <b>Safety Mode:</b> ✅ Ultra-Safe
⏰ <b>Check Interval:</b> 8-15 minutes
🔐 <b>Session:</b> {'✅ Valid' if self.session_valid else '❌ Expired'}

<b>Campaigns:</b>
{campaigns_list}

<b>Stats:</b>
📈 Checks: {self.stats['checks_made']}
🤖 Auto Bids: {self.stats['auto_bids_made']}
🎯 Safety Skips: {self.stats['safety_skips']}
            """
        self.send_telegram(status_msg)

    def send_safety_status(self):
        """Send safety status"""
        safety_msg = f"""
🛡️ <b>ULTRA-SAFE STEALTH MODE</b>

✅ <b>Active Safety Features:</b>
• Randomized check intervals (8-15 minutes)
• Smart bid increments (1-4, weighted +2)
• Human-like delays (2-8 seconds)
• Strategic skipping (15% chance)
• Daily action limit ({self.daily_action_limit})
• Occasional long breaks
• User-agent rotation
• Session persistence

📊 <b>Today's Usage:</b>
Actions: {self.action_count_today}/{self.daily_action_limit}
Safety Skips: {self.stats['safety_skips']}

🔒 <b>Detection Risk:</b> VERY LOW
        """
        self.send_telegram(safety_msg)

    def send_campaigns_list(self):
        """FIXED: Show campaigns with exact commands"""
        if not self.campaigns:
            self.send_telegram("📊 <b>No campaigns loaded yet.</b>\nSend /start to begin monitoring.")
            return
            
        campaigns_msg = "📊 <b>Your Campaigns:</b>\n\n"
        for name, data in self.campaigns.items():
            auto_status = "✅ ON" if data.get('auto_bid', False) else "❌ OFF"
            campaigns_msg += f"<b>{name}</b>\n"
            campaigns_msg += f"Your Bid: {data['my_bid']} credits\n"
            campaigns_msg += f"Auto-Bid: {auto_status}\n"
            campaigns_msg += f"<b>Command:</b> <code>/auto \"{name}\" on</code>\n\n"
        
        campaigns_msg += "💡 <b>Copy & paste the exact command above</b>"
        self.send_telegram(campaigns_msg)

    def send_help(self):
        """Send help"""
        help_msg = """
🤖 <b>Stealth Auto-Bid Bot</b>

/start - Start monitoring
/stop - Stop monitoring  
/status - Current status
/campaigns - List campaigns
/safety - Safety features

<b>Auto-Bid Commands:</b>
/auto all on - Enable all
/auto all off - Disable all
/auto "My Advert" on - Enable specific

<b>Examples:</b>
<code>/auto "My Advert" on</code>
<code>/auto all on</code>
<code>/auto leadsleap off</code>
        """
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        """FIXED: Extract clean campaign names"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                text_content = div.get_text().strip()
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if lines:
                    first_line = lines[0]
                    
                    # Extract clean name (stop at URL)
                    if 'http' in first_line:
                        campaign_name = first_line.split('http')[0].strip()
                    elif 'www.' in first_line:
                        campaign_name = first_line.split('www.')[0].strip()
                    else:
                        campaign_name = first_line
                    
                    # Clean up name
                    campaign_name = campaign_name.rstrip('.:- ')
                    
                    # Extract bid
                    bid_match = re.search(r'Campaign Bid:\s*(\d+)', text_content)
                    my_bid = int(bid_match.group(1)) if bid_match else 0
                    
                    if campaign_name and my_bid > 0:
                        campaigns[campaign_name] = {
                            'my_bid': my_bid,
                            'top_bid': my_bid,
                            'auto_bid': False,
                            'max_bid': self.default_max_bid,
                            'last_checked': None
                        }
                        logger.info(f"✅ Found: '{campaign_name}' - {my_bid} credits")
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error parsing campaigns: {e}")
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
            logger.error(f"Error getting top bid for {campaign_name}: {e}")
            return None

    def check_all_campaigns(self):
        """Check campaigns"""
        if not self.is_monitoring:
            return
            
        if self.should_skip_action("check"):
            return
            
        if self.occasional_long_break():
            return
            
        self.stats['checks_made'] += 1
        self.action_count_today += 1
        self.last_action_time = time.time()
        
        if not self.smart_login():
            logger.error("❌ Cannot login, skipping check")
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 3)
            
            self.campaigns = self.parse_campaigns(response.content)
            
            if not self.campaigns:
                logger.warning("No campaigns found")
                return
            
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now().strftime('%H:%M:%S')
                    
                    logger.info(f"📊 {campaign_name}: Your {campaign_data['my_bid']}, Top {top_bid}")
                    
                    if (campaign_data['auto_bid'] and 
                        top_bid > campaign_data['my_bid'] and 
                        not self.should_skip_action("bid")):
                        
                        self.execute_safe_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Error checking campaigns: {e}")

    def execute_safe_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        """Execute auto-bid"""
        try:
            new_bid = self.calculate_smart_bid(current_top_bid, campaign_data['my_bid'], campaign_name)
            
            if new_bid > campaign_data['max_bid']:
                logger.info(f"⏹️ {campaign_name}: Max bid reached")
                self.send_telegram(f"⏹️ <b>Max Bid Reached!</b>\n{campaign_name} at max {campaign_data['max_bid']} credits")
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
                logger.error(f"❌ No bid URL for {campaign_name}")
                return
            
            response = self.session.get(bid_url, timeout=30)
            self.human_delay(1, 3)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'bid'})
            
            if not form:
                logger.error(f"❌ No bid form for {campaign_name}")
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
🚀 <b>AUTO-BID SUCCESS!</b>

📊 <b>Campaign:</b> {campaign_name}
🎯 <b>Bid:</b> {campaign_data['my_bid']} → {new_bid} credits
📈 <b>Strategy:</b> Smart increment
💰 <b>Max Bid:</b> {campaign_data['max_bid']} credits

✅ <b>Now at #1 position!</b>
                """
                self.send_telegram(success_msg)
            else:
                logger.error(f"❌ Bid failed for {campaign_name}")
                
        except Exception as e:
            logger.error(f"❌ Auto-bid error: {e}")

    def run(self):
        """Main loop"""
        logger.info("🤖 Starting Ultra-Safe Stealth Bot...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🛡️ <b>Ultra-Safe Stealth Bot Activated!</b>\nUse /start to begin monitoring.")
        
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
                    logger.info(f"⏰ Next check in {next_check_interval//60} minutes")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                time.sleep(30)

# Start the bot
if __name__ == "__main__":
    bot = AdShareStealthBot()
    bot.run()
