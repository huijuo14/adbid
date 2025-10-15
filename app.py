import requests
from bs4 import BeautifulSoup
import time
import re
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class AdShareAutoBidBot:
    def __init__(self):
        # Telegram credentials
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        
        # AdShare credentials
        self.email = "loginallapps@gmail.com"
        self.password = "@Sd2007123"
        
        # Session management
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # Smart login settings - MINIMIZE LOGINS!
        self.last_login = None
        self.login_interval = 7200  # Only re-login every 2 hours (7200 seconds)
        self.session_valid = False
        self.consecutive_failures = 0
        
        # Bot settings
        self.is_monitoring = False
        self.check_interval = 300  # 5 minutes
        
        # Auto-bid settings
        self.campaigns = {}
        self.default_max_bid = 180
        self.default_increment = 2
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_made': 0,
            'auto_bids_made': 0,
            'logins_made': 0,
            'last_auto_bid': None
        }

    def smart_login(self):
        """
        SMART LOGIN: Only login when absolutely necessary
        - Reuses existing session as long as possible
        - Only re-logins every 2 hours or when session expires
        - Avoids breaking your other browser sessions
        """
        # If we recently logged in and session is still valid, reuse it
        if self.last_login and self.session_valid:
            time_since_login = (datetime.now() - self.last_login).total_seconds()
            if time_since_login < self.login_interval:
                logger.info("♻️ Using existing session")
                return True
        
        # Check if current session is still valid without logging in
        if self.check_session_valid():
            self.session_valid = True
            self.last_login = datetime.now()  # Refresh last login time
            logger.info("✅ Session still valid, reusing")
            return True
        
        # Only now do we actually login
        logger.info("🔐 Session expired, performing fresh login")
        return self.force_login()

    def check_session_valid(self):
        """Check if current session is still valid without making noise"""
        try:
            # Use a lightweight check that doesn't look like a full page load
            response = self.session.get("https://adsha.re/adverts", timeout=10, allow_redirects=False)
            
            # If we get redirected to login, session is invalid
            if response.status_code == 302 or "login" in response.headers.get('Location', ''):
                self.session_valid = False
                return False
            
            # If we can access the adverts page, session is valid
            self.session_valid = True
            return True
            
        except Exception as e:
            logger.error(f"Session check error: {e}")
            self.session_valid = False
            return False

    def force_login(self):
        """Perform fresh login only when absolutely necessary"""
        try:
            logger.info("🔄 Performing fresh login...")
            
            # Get login page
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find login form
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.error("Login form not found")
                return False
                
            # Get form action URL
            action_path = form.get('action', '')
            if action_path.startswith('http'):
                post_url = action_path
            else:
                post_url = f"https://adsha.re{action_path}"
            
            # Prepare login data
            login_data = {
                'mail': self.email,
                '04ce63a75551c350478884bcd8e6530f': self.password
            }
            
            # Submit login
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            
            # Verify login
            if self.check_session_valid():
                self.last_login = datetime.now()
                self.session_valid = True
                self.stats['logins_made'] += 1
                self.consecutive_failures = 0
                logger.info(f"✅ Login successful (Total logins: {self.stats['logins_made']})")
                return True
            else:
                self.consecutive_failures += 1
                logger.error(f"❌ Login failed (Consecutive failures: {self.consecutive_failures})")
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
        """Process incoming Telegram commands"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    if 'message' in update and 'text' in update['message']:
                        text = update['message']['text']
                        chat_id = update['message']['chat']['id']
                        
                        if text.startswith('/'):
                            self.handle_command(text, chat_id)
                            
        except Exception as e:
            logger.error(f"Command processing error: {e}")

    def handle_command(self, command, chat_id):
        """Handle specific commands"""
        command = command.lower().strip()
        
        if command == '/start':
            self.start_monitoring()
            self.send_telegram("🚀 <b>Auto-Bid Bot Started!</b>\nMonitoring your ads every 5 minutes.\nUse /auto to enable auto-bidding.")
            
        elif command == '/stop':
            self.stop_monitoring()
            self.send_telegram("🛑 <b>Auto-Bid Bot Stopped!</b>")
            
        elif command == '/status':
            self.send_status()
            
        elif command.startswith('/auto'):
            self.handle_auto_command(command)
            
        elif command == '/campaigns':
            self.send_campaigns_list()
            
        elif command == '/help':
            self.send_help()
            
        else:
            self.send_telegram("❌ Unknown command. Use /help for available commands.")

    def handle_auto_command(self, command):
        """Handle auto-bid commands"""
        parts = command.split()
        
        if len(parts) == 1:
            self.send_telegram("❌ Usage: /auto [campaign] on/off\nExample: /auto My Advert on")
            return
            
        if len(parts) == 2 and parts[1] in ['on', 'off']:
            # Enable/disable all campaigns
            for campaign_name in self.campaigns:
                self.campaigns[campaign_name]['auto_bid'] = (parts[1] == 'on')
            
            status = "enabled" if parts[1] == 'on' else "disabled"
            self.send_telegram(f"🔄 <b>Auto-bid {status} for all campaigns</b>")
            return
            
        if len(parts) >= 3:
            campaign_name = ' '.join(parts[1:-1])
            action = parts[-1]
            
            if campaign_name in self.campaigns:
                self.campaigns[campaign_name]['auto_bid'] = (action == 'on')
                status = "enabled" if action == 'on' else "disabled"
                self.send_telegram(f"🔄 <b>Auto-bid {status} for '{campaign_name}'</b>")
            else:
                self.send_telegram(f"❌ Campaign '{campaign_name}' not found. Use /campaigns to see available campaigns.")

    def start_monitoring(self):
        """Start monitoring"""
        self.is_monitoring = True
        self.stats['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("🚀 Monitoring started")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("🛑 Monitoring stopped")

    def send_status(self):
        """Send current status"""
        if not self.campaigns:
            status_msg = """
📊 <b>Bot Status</b>

🔄 <b>Monitoring:</b> ❌ Inactive
📈 <b>Campaigns:</b> Not loaded yet

💡 <b>Send /start to begin monitoring</b>
            """
        else:
            campaigns_list = ""
            for name, data in self.campaigns.items():
                status = "✅" if data.get('auto_bid', False) else "❌"
                campaigns_list += f"📊 {name}: {data['my_bid']} credits (Auto: {status})\n"
            
            status_msg = f"""
📊 <b>Bot Status</b>

🔄 <b>Monitoring:</b> {'✅ Active' if self.is_monitoring else '❌ Inactive'}
⏰ <b>Check Frequency:</b> {self.check_interval // 60} minutes
🔐 <b>Session:</b> {'✅ Valid' if self.session_valid else '❌ Expired'}

<b>Campaigns:</b>
{campaigns_list}

<b>Session Stats:</b>
📈 Checks Made: {self.stats['checks_made']}
🤖 Auto Bids: {self.stats['auto_bids_made']}
🔐 Logins: {self.stats['logins_made']}
            """
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        """Send list of available campaigns"""
        if not self.campaigns:
            self.send_telegram("📊 <b>No campaigns loaded yet.</b>\nSend /start to begin monitoring.")
            return
            
        campaigns_msg = "📊 <b>Your Campaigns:</b>\n\n"
        for name, data in self.campaigns.items():
            auto_status = "✅ ON" if data.get('auto_bid', False) else "❌ OFF"
            campaigns_msg += f"<b>{name}</b>\n"
            campaigns_msg += f"Your Bid: {data['my_bid']} credits\n"
            campaigns_msg += f"Auto-Bid: {auto_status}\n"
            campaigns_msg += f"Command: <code>/auto {name} on/off</code>\n\n"
        
        campaigns_msg += "💡 <b>Enable auto-bid:</b> <code>/auto Campaign Name on</code>"
        self.send_telegram(campaigns_msg)

    def send_help(self):
        """Send help message"""
        help_msg = """
🤖 <b>Auto-Bid Bot Commands</b>

/start - Start monitoring campaigns
/stop - Stop monitoring
/status - Current bot status
/campaigns - List your campaigns

<b>Auto-Bid Commands:</b>
/auto all on - Enable auto-bid for all
/auto all off - Disable auto-bid for all  
/auto "My Advert" on - Enable for specific campaign
/auto leadsleap off - Disable for specific campaign

<b>Examples:</b>
• Enable all: <code>/auto all on</code>
• Enable one: <code>/auto My Advert on</code>
• Disable one: <code>/auto leadsleap off</code>

💡 <b>Default Settings:</b>
Max Bid: 180 credits
Increment: +2 above top bid
        """
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        """Parse campaigns from adverts page HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            campaigns = {}
            
            # Find all campaign divs (they have border and padding)
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                # Extract campaign name (first line of text)
                lines = div.get_text().strip().split('\n')
                campaign_name = lines[0].strip() if lines else "Unknown"
                
                # Skip if it's empty or not a real campaign
                if not campaign_name or campaign_name in ['leadsleap', 'My Advert']:
                    campaign_name = lines[0].strip() if lines and lines[0].strip() else "Unknown"
                
                # Extract bid amount
                bid_match = re.search(r'Campaign Bid:\s*(\d+)', div.get_text())
                my_bid = int(bid_match.group(1)) if bid_match else 0
                
                if campaign_name and my_bid > 0:
                    campaigns[campaign_name] = {
                        'my_bid': my_bid,
                        'top_bid': my_bid,  # Will be updated from bid page
                        'auto_bid': False,  # Default off
                        'max_bid': self.default_max_bid,
                        'increment': self.default_increment,
                        'last_checked': None
                    }
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error parsing campaigns: {e}")
            return {}

    def get_top_bid_from_bid_page(self, campaign_name):
        """Get the actual top bid from the increase bid page"""
        try:
            # We need to find the increase bid URL first
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the increase bid link for this campaign
            increase_links = soup.find_all('a', href=re.compile(r'/adverts/bid/'))
            for link in increase_links:
                # Check if this link is in the right campaign section
                campaign_div = link.find_parent('div', style=re.compile(r'border.*solid.*#8CC63F'))
                if campaign_div and campaign_name in campaign_div.get_text():
                    bid_url = link['href']
                    if not bid_url.startswith('http'):
                        bid_url = f"https://adsha.re{bid_url}"
                    
                    # Now get the bid page
                    response = self.session.get(bid_url, timeout=30)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find top bid text
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
        """Check all campaigns for bid changes and auto-bid if enabled"""
        if not self.is_monitoring:
            return
            
        self.stats['checks_made'] += 1
        
        # SMART LOGIN: Only login when needed
        if not self.smart_login():
            logger.error("❌ Cannot login, skipping check")
            return
        
        try:
            # Get adverts page
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            
            # Parse campaigns
            self.campaigns = self.parse_campaigns(response.content)
            
            if not self.campaigns:
                logger.warning("No campaigns found on adverts page")
                return
            
            # Check each campaign
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = datetime.now().strftime('%H:%M:%S')
                    
                    logger.info(f"📊 {campaign_name}: Your bid {campaign_data['my_bid']}, Top bid {top_bid}")
                    
                    # Auto-bid logic
                    if campaign_data['auto_bid'] and top_bid > campaign_data['my_bid']:
                        self.execute_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"Error checking campaigns: {e}")

    def execute_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        """Execute auto-bid when outbid"""
        try:
            # Calculate new bid
            new_bid = current_top_bid + campaign_data['increment']
            
            # Check max bid limit
            if new_bid > campaign_data['max_bid']:
                logger.info(f"⏹️ {campaign_name}: Max bid {campaign_data['max_bid']} reached, skipping auto-bid")
                self.send_telegram(f"⏹️ <b>Max Bid Reached!</b>\n{campaign_name} at max {campaign_data['max_bid']} credits")
                return
            
            # Find increase bid URL
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
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
                logger.error(f"❌ Could not find bid URL for {campaign_name}")
                return
            
            # Submit bid increase
            response = self.session.get(bid_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            form = soup.find('form', {'name': 'bid'})
            if not form:
                logger.error(f"❌ Bid form not found for {campaign_name}")
                return
            
            # Get form action
            action = form.get('action', '')
            if not action.startswith('http'):
                action = f"https://adsha.re{action}"
            
            # Submit bid
            bid_data = {
                'bid': str(new_bid),
                'vis': '0'  # Default value
            }
            
            response = self.session.post(action, data=bid_data, allow_redirects=True)
            
            # Verify bid was successful
            if response.status_code == 200:
                self.stats['auto_bids_made'] += 1
                self.stats['last_auto_bid'] = datetime.now().strftime('%H:%M:%S')
                campaign_data['my_bid'] = new_bid
                
                logger.info(f"🚀 AUTO-BID: {campaign_name} → {new_bid} credits")
                
                # Send success message
                success_msg = f"""
🚀 <b>AUTO-BID SUCCESS!</b>

📊 <b>Campaign:</b> {campaign_name}
🎯 <b>Bid:</b> {campaign_data['my_bid']} → {new_bid} credits
📈 <b>Strategy:</b> +{campaign_data['increment']} above top bid ({current_top_bid})
💰 <b>Max Bid:</b> {campaign_data['max_bid']} credits
🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

✅ <b>Now at #1 position!</b>
                """
                self.send_telegram(success_msg)
            else:
                logger.error(f"❌ Bid increase failed for {campaign_name}")
                
        except Exception as e:
            logger.error(f"❌ Auto-bid error for {campaign_name}: {e}")

    def run(self):
        """Main bot loop with SMART session management"""
        logger.info("🤖 Starting AdShare Auto-Bid Bot...")
        
        # Initial login
        if not self.force_login():
            logger.error("❌ Initial login failed")
            return
        
        self.send_telegram("🤖 <b>Auto-Bid Bot Started!</b>\nUse /start to begin monitoring.\nUse /help for commands.")
        
        check_count = 0
        while True:
            try:
                # Process Telegram commands every minute
                if check_count % 1 == 0:
                    self.process_telegram_command()
                
                # Check campaigns every interval (only if monitoring)
                if self.is_monitoring and check_count % (self.check_interval // 60) == 0:
                    self.check_all_campaigns()
                
                check_count += 1
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                time.sleep(30)

# Start the bot
if __name__ == "__main__":
    bot = AdShareAutoBidBot()
    bot.run()
