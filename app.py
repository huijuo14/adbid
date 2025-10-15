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
    return "🤖 AdShare Efficiency Bot - Maximum Top Position, Minimum Credits"

@app.route('/health')
def health():
    return "✅ Bot Healthy - Efficiency Mode Active"

class AdShareEfficiencyBot:
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
        
        # 🎯 EFFICIENCY SETTINGS
        self.is_monitoring = False
        self.campaigns = {}
        
        # 💰 CREDIT OPTIMIZATION
        self.default_max_bid = 369  # Your preferred max
        self.efficiency_mode = True  # Smart credit saving
        
        # ⚡ SMART TIMING
        self.check_intervals = {
            'active_competition': (180, 300),    # 3-5 min when competing
            'normal': (300, 600),               # 5-10 min normally
            'dominant': (600, 900)              # 10-15 min when winning
        }
        
        # 🎯 SMART BIDDING STRATEGIES
        self.bid_strategies = {
            'efficient': [1, 1, 1, 2, 2, 2, 3],  # Minimum to win
            'aggressive': [2, 2, 3, 3, 4, 4, 5], # Dominate quickly
            'stealth': [1, 1, 2, 2, 2, 3, 3]     # Slow and steady
        }
        self.current_strategy = 'efficient'
        
        # 📊 EFFICIENCY TRACKING
        self.efficiency_stats = {
            'credits_saved': 0,
            'time_at_top': 0,
            'smart_skips': 0,
            'unnecessary_bids_avoided': 0
        }
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'last_auto_bid': None
        }

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

    def get_smart_check_interval(self, campaign_name):
        """Smart interval based on competition level"""
        if campaign_name in self.campaigns:
            campaign_data = self.campaigns[campaign_name]
            
            # If we're not at top, check more frequently
            if campaign_data.get('top_bid', 0) > campaign_data.get('my_bid', 0):
                return random.randint(*self.check_intervals['active_competition'])
            # If we're dominating, check less frequently
            elif campaign_data.get('my_bid', 0) - campaign_data.get('top_bid', 0) >= 5:
                return random.randint(*self.check_intervals['dominant'])
        
        return random.randint(*self.check_intervals['normal'])

    def calculate_efficient_bid(self, current_top_bid, my_bid, campaign_name):
        """Smart bidding that maximizes position while minimizing cost"""
        strategy_weights = self.bid_strategies[self.current_strategy]
        base_increment = random.choice(strategy_weights)
        
        # 🎯 EFFICIENCY RULES:
        
        # Rule 1: If we were recently outbid, be slightly more aggressive
        campaign_data = self.campaigns.get(campaign_name, {})
        if campaign_data.get('last_outbid_time'):
            time_since_outbid = (datetime.now() - campaign_data['last_outbid_time']).total_seconds()
            if time_since_outbid < 600:  # Within 10 minutes of being outbid
                base_increment = min(base_increment + 1, 5)
        
        # Rule 2: If we've been stable at top, be conservative
        if my_bid >= current_top_bid and campaign_data.get('stable_top_time', 0) > 3600:
            base_increment = max(1, base_increment - 1)
        
        new_bid = current_top_bid + base_increment
        
        # Rule 3: Never exceed max bid
        campaign_max = campaign_data.get('max_bid', self.default_max_bid)
        new_bid = min(new_bid, campaign_max)
        
        # Track efficiency
        if new_bid - current_top_bid < 3:
            self.efficiency_stats['credits_saved'] += (3 - (new_bid - current_top_bid))
        
        return new_bid

    def should_skip_bid_for_efficiency(self, campaign_name, current_top_bid, my_bid):
    """Smart skipping with random 1-7 minute hold"""
    campaign_data = self.campaigns.get(campaign_name, {})
    
    # Skip if we're already at top
    if my_bid >= current_top_bid:
        self.efficiency_stats['unnecessary_bids_avoided'] += 1
        return True
    
    # Skip if the gap is too small (might be temporary fluctuation)
    if current_top_bid - my_bid <= 1:
        if random.random() < 0.3:  # 30% chance to skip small gaps
            self.efficiency_stats['smart_skips'] += 1
            return True
    
    # 🎯 RANDOM HOLD: 1-7 minutes (instead of fixed 5)
    last_bid_time = campaign_data.get('last_bid_time')
    if last_bid_time:
        time_since_last_bid = (datetime.now() - last_bid_time).total_seconds()
        
        # Generate random hold time between 1-7 minutes (60-420 seconds)
        random_hold_time = random.randint(60, 420)
        
        if time_since_last_bid < random_hold_time:
            # 30% chance to skip during hold period
            if random.random() < 0.3:
                self.efficiency_stats['smart_skips'] += 1
                logger.info(f"⏳ Holding bid for {random_hold_time//60}min (random hold)")
                return True
    
    return False
    
    def smart_login(self):
        """Efficient login management"""
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
        except:
            self.session_valid = False
            return False

    def force_login(self):
        """Efficient login"""
        try:
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
        except:
            return False

    def process_telegram_command(self):
        """Process commands"""
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
            self.send_status()
        elif command_lower.startswith('/auto'):
            self.handle_auto_command(command)
        elif command_lower == '/campaigns':
            self.send_campaigns_list()
        elif command_lower == '/efficiency':
            self.send_efficiency_report()
        elif command_lower == '/strategy':
            self.handle_strategy_command(command)
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

    def handle_strategy_command(self, command):
        """Change bidding strategy"""
        parts = command.split()
        if len(parts) == 2:
            strategy = parts[1].lower()
            if strategy in self.bid_strategies:
                self.current_strategy = strategy
                self.send_telegram(f"🎯 Strategy changed to: {strategy}")
            else:
                self.send_telegram(f"❌ Available strategies: efficient, aggressive, stealth")

    def start_monitoring(self):
        """Start monitoring"""
        self.is_monitoring = True
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("🚀 Efficiency monitoring started")
        self.send_telegram("🚀 Efficiency Bot Activated!\nMaximizing top position, minimizing credits!")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")
        self.send_telegram("🛑 Bot Stopped!")

    def send_status(self):
        """Send status with efficiency info"""
        if not self.campaigns:
            self.send_telegram("📊 No campaigns loaded. Send /start")
            return
            
        campaigns_list = ""
        top_position_count = 0
        total_campaigns = len(self.campaigns)
        
        for name, data in self.campaigns.items():
            status = "✅" if data.get('auto_bid', False) else "❌"
            position = "🏆 TOP" if data.get('my_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
            if position == "🏆 TOP":
                top_position_count += 1
            campaigns_list += f"{position} {name}: {data['my_bid']} credits (Auto: {status})\n"
        
        efficiency_rate = (top_position_count / total_campaigns * 100) if total_campaigns > 0 else 0
        
        status_msg = f"""
📊 EFFICIENCY STATUS

🏆 Top Position: {top_position_count}/{total_campaigns} ({efficiency_rate:.1f}%)
🎯 Strategy: {self.current_strategy}
🔄 Monitoring: {'✅ Active' if self.is_monitoring else '❌ Inactive'}

{campaigns_list}
💎 Credits Saved: {self.efficiency_stats['credits_saved']}
🤖 Smart Skips: {self.efficiency_stats['smart_skips']}
        """
        self.send_telegram(status_msg)

    def send_efficiency_report(self):
        """Send detailed efficiency report"""
        report = f"""
💎 EFFICIENCY REPORT

🏆 Performance:
• Credits Saved: {self.efficiency_stats['credits_saved']}
• Smart Skips: {self.efficiency_stats['smart_skips']}
• Unnecessary Bids Avoided: {self.efficiency_stats['unnecessary_bids_avoided']}

🎯 Current Strategy: {self.current_strategy}
📊 Auto-Bids: {self.stats['auto_bids_made']}
⏰ Checks: {self.stats['checks_made']}

💡 Tips:
• Use /strategy efficient (save credits)
• Use /strategy aggressive (dominate faster)
• Use /strategy stealth (slow and steady)
        """
        self.send_telegram(report)

    def send_campaigns_list(self):
        """Show campaigns"""
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
        """Send help"""
        help_msg = """
🤖 EFFICIENCY BOT COMMANDS

/start - Start monitoring
/stop - Stop monitoring  
/status - Efficiency status
/campaigns - List campaigns
/efficiency - Detailed report

/auto "My Advert" on - Enable auto-bid
/auto all on - Enable all

/strategy efficient - Save credits (default)
/strategy aggressive - Dominate faster
/strategy stealth - Slow and steady

💡 Goal: Maximum top position, minimum credits!
        """
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        """Extract campaign data"""
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
                            'last_checked': None,
                            'last_bid_time': None,
                            'last_outbid_time': None,
                            'stable_top_time': 0
                        }
            
            return new_campaigns
        except:
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
        """Efficient campaign checking"""
        if not self.is_monitoring:
            return
            
        self.stats['checks_made'] += 1
        self.action_count_today += 1
        self.last_action_time = time.time()
        
        if not self.smart_login():
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    # Update bid info while preserving settings
                    old_bid = self.campaigns[campaign_name]['my_bid']
                    self.campaigns[campaign_name]['my_bid'] = new_data['my_bid']
                    self.campaigns[campaign_name]['top_bid'] = new_data['top_bid']
                    
                    # Track position stability
                    if new_data['my_bid'] >= new_data['top_bid']:
                        self.campaigns[campaign_name]['stable_top_time'] += 300  # 5 minutes
                    else:
                        self.campaigns[campaign_name]['stable_top_time'] = 0
                        self.campaigns[campaign_name]['last_outbid_time'] = datetime.now()
                else:
                    self.campaigns[campaign_name] = new_data
            
            if not self.campaigns:
                return
            
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    # Update top bid
                    old_top_bid = campaign_data.get('top_bid', 0)
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now()
                    
                    # 🎯 EFFICIENCY AUTO-BID LOGIC
                    if (campaign_data['auto_bid'] and 
                        not self.should_skip_bid_for_efficiency(campaign_name, top_bid, campaign_data['my_bid'])):
                        
                        self.execute_efficient_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Check error: {e}")

    def execute_efficient_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        """Execute efficient auto-bid"""
        try:
            old_bid = campaign_data['my_bid']
            new_bid = self.calculate_efficient_bid(current_top_bid, old_bid, campaign_name)
            
            if new_bid > campaign_data['max_bid']:
                return
            
            # Only bid if actually needed
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
                # ✅ SUCCESS: Update FIRST, then send message
                campaign_data['my_bid'] = new_bid
                campaign_data['last_bid_time'] = datetime.now()
                
                self.stats['auto_bids_made'] += 1
                self.action_count_today += 1
                self.stats['last_auto_bid'] = datetime.now().strftime('%H:%M:%S')
                
                logger.info(f"🚀 EFFICIENT BID: {campaign_name} {old_bid}→{new_bid}")
                
                # 🎯 EFFICIENCY-FOCUSED MESSAGE
                increase = new_bid - old_bid
                efficiency_note = ""
                if increase <= 2:
                    efficiency_note = "💎 Efficient bid!"
                elif increase >= 4:
                    efficiency_note = "⚡ Aggressive move"
                
                success_msg = f"""
🚀 AUTO-BID SUCCESS! {efficiency_note}

📊 Campaign: {campaign_name}
🎯 Bid: {old_bid} → {new_bid} credits
📈 Increase: +{increase} credits
🏆 Position: #1 Achieved!

💡 Strategy: {self.current_strategy}
                """
                self.send_telegram(success_msg)
                
        except Exception as e:
            logger.error(f"Bid error: {e}")

    def run(self):
        """Main efficiency loop"""
        logger.info("🤖 Starting Efficiency Bot...")
        
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("💎 Efficiency Bot Activated!\nGoal: Maximum top position, minimum credits!")
        
        last_command_check = 0
        last_campaign_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                if self.is_monitoring and current_time - last_campaign_check >= 300:  # 5 min base
                    self.check_all_campaigns()
                    last_campaign_check = current_time
                
                time.sleep(1)
                
            except Exception as e:
                time.sleep(30)

def run_bot():
    """Run the bot"""
    bot = AdShareEfficiencyBot()
    bot.run()

if __name__ == "__main__":
    # Start bot in background
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask for Render
    app.run(host='0.0.0.0', port=10000, debug=False)
