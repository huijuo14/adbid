import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import random
from datetime import datetime
import os
import json

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

class UltimateSmartBidder:
    def __init__(self):
        # Environment variables
        self.bot_token = os.environ.get('BOT_TOKEN', "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc")
        self.chat_id = os.environ.get('CHAT_ID', "2052085789")
        self.email = os.environ.get('EMAIL', "loginallapps@gmail.com")
        self.password = os.environ.get('PASSWORD', "@Sd2007123")
        self.last_update_id = 0
        
        self.session = requests.Session()
        self.rotate_user_agent()
        self.session_valid = False
        
        self.is_monitoring = False
        self.campaigns = {}
        
        # NEW: Market monitoring
        self.market_bids = {}  # All bids in market
        self.bid_history = {}  # Historical bid data
        self.market_alerts_sent = set()  # Prevent duplicate alerts
        
        # Configurable settings
        self.minimal_bid_weights = [1, 2]
        self.check_interval = int(os.environ.get('CHECK_INTERVAL', '180'))  # 3 minutes
        self.max_bid_limit = int(os.environ.get('MAX_BID_LIMIT', '369'))
        self.bid_cooldown = 60
        
        # NEW: Market monitoring settings
        self.market_check_interval = int(os.environ.get('MARKET_CHECK_INTERVAL', '300'))  # 5 minutes
        self.bid_change_threshold = int(os.environ.get('BID_CHANGE_THRESHOLD', '5'))  # Min change to alert
        self.enable_market_alerts = True
        
        self.visitor_alert_threshold = int(os.environ.get('VISITOR_ALERT_THRESHOLD', '1000'))
        self.visitor_stop_threshold = int(os.environ.get('VISITOR_STOP_THRESHOLD', '500'))
        self.current_traffic_credits = 0
        self.current_visitor_credits = 0
        self.last_credit_alert = None
        
        # Basic tracking
        self.last_bid_time = {}
        self.sent_alerts = {}
        
        logger.info(f"BOT_INITIALIZED - Market monitoring: {self.enable_market_alerts}")

    def rotate_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        self.session.headers.update({'User-Agent': random.choice(user_agents)})

    def human_delay(self, min_seconds=2, max_seconds=5):
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def force_login(self):
        try:
            logger.info("LOGIN_ATTEMPT - Starting login process")
            self.human_delay(2, 4)
            
            login_url = "https://adsha.re/login"
            response = self.session.get(login_url, timeout=30)
            self.human_delay(1, 2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.error("LOGIN_FAILED - Login form not found")
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
                logger.error("LOGIN_FAILED - Password field not found")
                return False
            
            login_data = {
                'mail': self.email,
                password_field: self.password
            }
            
            response = self.session.post(post_url, data=login_data, allow_redirects=True)
            self.human_delay(1, 2)
            
            if self.check_session_valid():
                self.session_valid = True
                logger.info("LOGIN_SUCCESS - Session active")
                return True
            
            logger.error("LOGIN_FAILED - Session validation failed")
            return False
        except Exception as e:
            logger.error(f"LOGIN_ERROR - {e}")
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
            logger.info("SESSION_VALID - Session still active")
            self.session_valid = True
            return True
        
        logger.warning("SESSION_EXPIRED - Re-login required")
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
        except Exception as e:
            logger.error(f"TRAFFIC_CREDITS_ERROR - {e}")
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
            logger.error(f"VISITOR_CREDITS_ERROR - {e}")
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

    def send_telegram(self, message, parse_mode='HTML'):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id, 
                "text": message, 
                "parse_mode": parse_mode
            }
            response = self.session.post(url, json=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"TELEGRAM_SEND_ERROR - {e}")
            return False

    # NEW: Market Monitoring Functions
    def scan_market_bids(self):
        """Scan ALL campaigns in the market and track their bids"""
        try:
            logger.info("MARKET_SCAN - Scanning all market bids")
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            current_market = {}
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                campaign_name = self.extract_campaign_name(div)
                if not campaign_name:
                    continue
                
                # Get current bid
                bid_match = re.search(r'Campaign Bid:\s*(\d+)', div.get_text())
                current_bid = int(bid_match.group(1)) if bid_match else 0
                
                if campaign_name and current_bid > 0:
                    current_market[campaign_name] = current_bid
                    
                    # Initialize bid history
                    if campaign_name not in self.bid_history:
                        self.bid_history[campaign_name] = []
                    
                    # Record bid with timestamp
                    self.bid_history[campaign_name].append({
                        'bid': current_bid,
                        'timestamp': datetime.now().isoformat(),
                        'type': 'market_scan'
                    })
                    
                    # Keep only last 50 records
                    if len(self.bid_history[campaign_name]) > 50:
                        self.bid_history[campaign_name] = self.bid_history[campaign_name][-50:]
            
            # Check for market changes
            self.analyze_market_changes(current_market)
            self.market_bids = current_market
            
            logger.info(f"MARKET_SCAN_COMPLETE - Found {len(current_market)} campaigns")
            return current_market
            
        except Exception as e:
            logger.error(f"MARKET_SCAN_ERROR - {e}")
            return {}

    def extract_campaign_name(self, div_element):
        """Extract campaign name from div element"""
        try:
            campaign_name = ""
            for element in div_element.contents:
                if isinstance(element, str) and element.strip():
                    campaign_name = element.strip()
                    break
                elif element.name == 'br':
                    break
            
            if 'http' in campaign_name:
                campaign_name = campaign_name.split('http')[0].strip()
            campaign_name = campaign_name.rstrip('.:- ')
            
            return campaign_name
        except Exception as e:
            logger.error(f"EXTRACT_CAMPAIGN_NAME_ERROR - {e}")
            return ""

    def analyze_market_changes(self, current_market):
        """Analyze market changes and send alerts"""
        if not hasattr(self, 'previous_market_bids'):
            self.previous_market_bids = current_market
            return
        
        # Check for new campaigns
        new_campaigns = set(current_market.keys()) - set(self.previous_market_bids.keys())
        for campaign in new_campaigns:
            if campaign not in self.market_alerts_sent:
                self.send_telegram(f"🆕 NEW CAMPAIGN:\n\"{campaign}\"\nStarting bid: {current_market[campaign]} credits")
                self.market_alerts_sent.add(campaign)
                logger.info(f"NEW_CAMPAIGN_ALERT - {campaign} | {current_market[campaign]} credits")
        
        # Check for removed campaigns
        removed_campaigns = set(self.previous_market_bids.keys()) - set(current_market.keys())
        for campaign in removed_campaigns:
            if f"removed_{campaign}" not in self.market_alerts_sent:
                self.send_telegram(f"❌ CAMPAIGN ENDED:\n\"{campaign}\"")
                self.market_alerts_sent.add(f"removed_{campaign}")
                logger.info(f"CAMPAIGN_ENDED_ALERT - {campaign}")
        
        # Check for bid changes
        for campaign, current_bid in current_market.items():
            previous_bid = self.previous_market_bids.get(campaign)
            
            if previous_bid and previous_bid != current_bid:
                change = current_bid - previous_bid
                change_abs = abs(change)
                
                # Only alert on significant changes
                if change_abs >= self.bid_change_threshold:
                    alert_key = f"bid_change_{campaign}_{current_bid}"
                    if alert_key not in self.market_alerts_sent:
                        change_type = "📈 INCREASE" if change > 0 else "📉 DECREASE"
                        change_emoji = "🚀" if change > 10 else "⬆️" if change > 0 else "⬇️"
                        
                        message = f"{change_emoji} MARKET BID {change_type}:\n\"{campaign}\"\n"
                        message += f"Previous: {previous_bid} → Current: {current_bid} credits\n"
                        message += f"Change: {change:+d} credits"
                        
                        self.send_telegram(message)
                        self.market_alerts_sent.add(alert_key)
                        logger.info(f"MARKET_BID_CHANGE - {campaign} | {previous_bid} → {current_bid}")
        
        self.previous_market_bids = current_market

    def get_market_analytics(self):
        """Get market analytics summary"""
        if not self.market_bids:
            return "No market data available"
        
        total_campaigns = len(self.market_bids)
        avg_bid = sum(self.market_bids.values()) / total_campaigns
        min_bid = min(self.market_bids.values())
        max_bid = max(self.market_bids.values())
        
        analytics = f"""
📊 MARKET ANALYTICS

Total Campaigns: {total_campaigns}
Average Bid: {avg_bid:.1f} credits
Bid Range: {min_bid} - {max_bid} credits

Top 5 Highest Bids:
"""
        
        # Top 5 highest bids
        sorted_bids = sorted(self.market_bids.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (campaign, bid) in enumerate(sorted_bids, 1):
            analytics += f"{i}. {campaign}: {bid} credits\n"
        
        return analytics

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
        except Exception as e:
            logger.error(f"TELEGRAM_COMMAND_ERROR - {e}")

    def handle_command(self, command, chat_id):
        command_lower = command.lower().strip()
        
        if command_lower == '/start':
            self.start_monitoring()
        elif command_lower == '/stop':
            self.stop_monitoring()
        elif command_lower == '/status':
            self.send_enhanced_status()
        elif command_lower == '/campaigns':
            self.send_campaigns_list()
        elif command_lower == '/credits':
            self.send_credit_status()
        elif command_lower.startswith('/auto'):
            self.handle_auto_command(command)
        elif command_lower == '/help':
            self.send_enhanced_help()
        elif command_lower == '/market':  # NEW: Market command
            self.send_market_report()
        elif command_lower == '/analytics':  # NEW: Analytics command
            self.send_market_analytics()
        else:
            self.send_telegram("❌ Unknown command. Use /help for available commands")

    def send_market_report(self):
        """Send current market overview"""
        if not self.market_bids:
            self.scan_market_bids()
        
        if not self.market_bids:
            self.send_telegram("📊 No market data available yet. Scanning...")
            return
        
        report = f"""
🏪 MARKET OVERVIEW

Total Active Campaigns: {len(self.market_bids)}
Current Market Range: {min(self.market_bids.values())} - {max(self.market_bids.values())} credits

🔝 Top 3 Highest Bids:
"""
        
        sorted_bids = sorted(self.market_bids.items(), key=lambda x: x[1], reverse=True)[:3]
        for i, (campaign, bid) in enumerate(sorted_bids, 1):
            report += f"{i}. {campaign}: {bid} credits\n"
        
        report += f"\n🔄 Market monitoring: {'✅ ACTIVE' if self.enable_market_alerts else '❌ INACTIVE'}"
        
        self.send_telegram(report)

    def send_market_analytics(self):
        """Send detailed market analytics"""
        analytics = self.get_market_analytics()
        self.send_telegram(analytics)

    def handle_auto_command(self, command):
        parts = command.split()
        
        if len(parts) == 1:
            self.send_telegram("❌ Usage: /auto [campaign] on/off\nOr: /auto all on/off")
            return
            
        if len(parts) == 2 and parts[1].lower() in ['on', 'off']:
            action = parts[1].lower()
            self.toggle_all_auto_bid(action == 'on')
            return
            
        if len(parts) == 3 and parts[1].lower() == 'all':
            action = parts[2].lower()
            self.toggle_all_auto_bid(action == 'on')
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
                self.toggle_auto_bid(found_campaign, action == 'on')

    def toggle_auto_bid(self, campaign_name, enable):
        if campaign_name in self.campaigns:
            self.campaigns[campaign_name]['auto_bid'] = enable
            status = "enabled" if enable else "disabled"
            self.send_telegram(f"🔄 Auto-bid {status} for '{campaign_name}'")
            logger.info(f"AUTO_BID_TOGGLE - {campaign_name} | {status}")

    def toggle_all_auto_bid(self, enable):
        for campaign_name in self.campaigns:
            self.campaigns[campaign_name]['auto_bid'] = enable
        
        status = "enabled" if enable else "disabled"
        self.send_telegram(f"🔄 Auto-bid {status} for all campaigns")
        logger.info(f"AUTO_BID_ALL_TOGGLE - All campaigns | {status}")

    def start_monitoring(self):
        self.is_monitoring = True
        self.enable_market_alerts = True
        logger.info("BOT_STARTED - Monitoring activated with market scanning")
        self.send_telegram("🚀 Ultimate Smart Bidder ACTIVATED!\n\nMonitoring all campaigns + market bids...")
        self.send_enhanced_status()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.enable_market_alerts = False
        logger.info("BOT_STOPPED - Monitoring stopped")
        self.send_telegram("🛑 Bot STOPPED!\nUse /start to resume monitoring.")

    def send_enhanced_status(self):
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
            
        status_msg = f"""
📊 ENHANCED STATUS REPORT

💰 CREDITS:
Traffic: {traffic_credits} | Visitors: {visitor_credits:,}

🏆 YOUR CAMPAIGNS:
"""
        
        if self.campaigns:
            for name, data in self.campaigns.items():
                is_top = data.get('my_bid', 0) >= data.get('top_bid', 0)
                status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
                position = "🏆 #1" if is_top else f"📉 #{data.get('position', '2+')}"
                
                views_info = ""
                if 'views' in data:
                    views = data['views']
                    progress_pct = (views['current'] / views['total'] * 100) if views['total'] > 0 else 0
                    views_info = f"\n   📈 Progress: {views['current']:,}/{views['total']:,} ({progress_pct:.1f}%)"
                
                status_msg += f"{position} {name}\n"
                status_msg += f"   💰 Bid: {data['my_bid']} | Top: {data.get('top_bid', 'N/A')} | {status}{views_info}\n\n"
        else:
            status_msg += "No active campaigns\n\n"

        # Add market info
        if self.market_bids:
            status_msg += f"🏪 MARKET:\nActive Campaigns: {len(self.market_bids)}\nBid Range: {min(self.market_bids.values())}-{max(self.market_bids.values())} credits\n\n"

        status_msg += "🤖 Bot is actively monitoring market + your campaigns..."
        self.send_telegram(status_msg)

    def send_campaigns_list(self):
        if not self.campaigns:
            self.send_telegram("📊 No campaigns found yet. The bot is monitoring adsha.re for campaigns...")
            return
        
        campaigns_text = "📋 YOUR CAMPAIGNS\n\n"
        
        for name, data in self.campaigns.items():
            auto_status = "✅ AUTO" if data.get('auto_bid', False) else "❌ MANUAL"
            position = "🏆 #1" if data.get('my_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
            
            campaigns_text += f"{position} <b>{name}</b>\n"
            campaigns_text += f"   💰 Your Bid: {data['my_bid']} | Top Bid: {data.get('top_bid', 'N/A')} | {auto_status}\n"
            
            if 'views' in data:
                views = data['views']
                progress_pct = (views['current'] / views['total'] * 100) if views['total'] > 0 else 0
                campaigns_text += f"   📈 Progress: {views['current']:,}/{views['total']:,} ({progress_pct:.1f}%)\n"
            
            campaigns_text += "\n"
        
        campaigns_text += "💡 Use /auto [campaign] on/off to control auto-bidding"
        self.send_telegram(campaigns_text)

    def send_credit_status(self):
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        
        credit_msg = f"""
💰 CREDIT MANAGEMENT

Traffic Credits: {traffic_credits}
Visitor Credits: {visitor_credits:,}
"""
        
        if traffic_credits >= 1000:
            credit_msg += "\n💡 RECOMMENDATION: Convert traffic credits to visitors!\n"
        
        if visitor_credits < 1000:
            credit_msg += "⚠️ WARNING: Visitor credits getting low.\n"
        
        if visitor_credits < 500:
            credit_msg += "🛑 CRITICAL: Very low visitors. Auto-bid will stop soon.\n"
        
        credit_msg += f"\nAuto-bid status: {'✅ ACTIVE' if self.is_monitoring else '❌ PAUSED'}"
        
        self.send_telegram(credit_msg)

    def send_enhanced_help(self):
        help_msg = """
🤖 ULTIMATE SMART BIDDER - MARKET EDITION

📋 AVAILABLE COMMANDS:

/start - Start 24/7 monitoring + market scanning
/stop - Stop monitoring  
/status - Enhanced status with analytics
/campaigns - List your campaigns with details
/credits - Credit management overview
/market - Current market overview 🆕
/analytics - Detailed market analytics 🆕

⚙️ AUTO-BID CONTROL:
/auto all on/off - Toggle all campaigns
/auto [campaign] on/off - Toggle specific campaign

🎯 CORE FEATURES:
• 24/7 campaign monitoring
• Auto-bidding to maintain #1 position
• ALWAYS-ON market bid tracking 🆕
• Bid change alerts (even for campaigns you don't own) 🆕
• New campaign alerts 🆕
• Market analytics and trends 🆕
• Credit protection system

💡 TIP: Use /market to see current bid opportunities!
"""
        self.send_telegram(help_msg)

    def parse_campaigns(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            new_campaigns = {}
            
            campaign_divs = soup.find_all('div', style=re.compile(r'border.*solid.*#8CC63F'))
            
            for div in campaign_divs:
                campaign_name = self.extract_campaign_name(div)
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
            logger.error(f"PARSE_CAMPAIGNS_ERROR - {e}")
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
        except Exception as e:
            logger.error(f"GET_TOP_BID_ERROR - {e}")
            return None

    def calculate_minimal_bid(self, current_top_bid):
        new_bid = current_top_bid + random.choice(self.minimal_bid_weights)
        
        if new_bid > self.max_bid_limit:
            self.send_telegram(f"🛑 MAX BID LIMIT: Would bid {new_bid} but max is {self.max_bid_limit}!")
            return None
        
        return new_bid

    def check_completion_alerts(self, campaign_name, campaign_data):
        if 'views' not in campaign_data:
            return
            
        current = campaign_data['views']['current']
        total = campaign_data['views']['total']
        
        if total == 0:
            return
            
        completion_ratio = current / total
        alert_key = f"{campaign_name}_99"
        
        if completion_ratio >= 0.99:
            if alert_key not in self.sent_alerts:
                self.send_telegram(f"✅ Campaign Completed:\n\"{campaign_name}\" - {current:,}/{total:,} views (100%)\n🚨 EXTEND NOW - Bid reset to 0!")
                self.sent_alerts[alert_key] = True
                logger.warning(f"COMPLETION_ALERT - {campaign_name} | 99% complete")

    def execute_smart_auto_bid(self, campaign_name, campaign_data, current_top_bid):
        try:
            if campaign_data['my_bid'] >= current_top_bid:
                return
            
            # Rate limiting check
            current_time = time.time()
            last_bid = self.last_bid_time.get(campaign_name, 0)
            if current_time - last_bid < self.bid_cooldown:
                logger.info(f"RATE_LIMITED - {campaign_name} | Cooldown active")
                return
            
            old_bid = campaign_data['my_bid']
            new_bid = self.calculate_minimal_bid(current_top_bid)
            
            if new_bid is None:
                return
                
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
                self.last_bid_time[campaign_name] = time.time()
                
                logger.info(f"AUTO_BID_SUCCESS - {campaign_name} | {old_bid} → {new_bid} | Regained #1")
                
                success_msg = f"""
🚀 AUTO-BID SUCCESS!

📊 Campaign: {campaign_name}
🎯 Bid: {old_bid} → {new_bid} credits
📈 Increase: +{new_bid - old_bid} credits
🏆 Position: #1 Achieved!
"""
                self.send_telegram(success_msg)
                
        except Exception as e:
            logger.error(f"AUTO_BID_ERROR - {campaign_name} | {e}")

    def check_all_campaigns(self):
        if not self.is_monitoring:
            return
        
        if not self.smart_login():
            logger.error("CAMPAIGN_CHECK_FAILED - Cannot check campaigns - login failed")
            return
        
        try:
            adverts_url = "https://adsha.re/adverts"
            response = self.session.get(adverts_url, timeout=30)
            self.human_delay(1, 2)
            
            new_campaigns_data = self.parse_campaigns(response.content)
            
            # NEW: Always scan market bids
            if self.enable_market_alerts:
                self.scan_market_bids()
            
            # Track bid changes even with no campaigns
            if not self.campaigns and new_campaigns_data:
                logger.info(f"NEW_CAMPAIGNS_DETECTED - Found {len(new_campaigns_data)} campaigns")
            
            for campaign_name, new_data in new_campaigns_data.items():
                if campaign_name in self.campaigns:
                    auto_bid = self.campaigns[campaign_name].get('auto_bid', False)
                    old_top_bid = self.campaigns[campaign_name].get('top_bid', 0)
                    
                    self.campaigns[campaign_name].update(new_data)
                    self.campaigns[campaign_name]['auto_bid'] = auto_bid
                    
                    # Check for bid changes
                    new_top_bid = new_data.get('top_bid', 0)
                    if old_top_bid > 0 and old_top_bid != new_top_bid:
                        if new_top_bid < old_top_bid:
                            self.send_telegram(f"🔔 BID DECREASE:\n\"{campaign_name}\" - Top bid dropped from {old_top_bid} to {new_top_bid}!")
                            logger.warning(f"BID_CHANGE - {campaign_name} | {old_top_bid} → {new_top_bid} | Decrease")
                        elif new_top_bid > old_top_bid:
                            self.send_telegram(f"📈 BID INCREASE:\n\"{campaign_name}\" - Top bid rose from {old_top_bid} to {new_top_bid}!")
                            logger.warning(f"BID_CHANGE - {campaign_name} | {old_top_bid} → {new_top_bid} | Increase")
                else:
                    self.campaigns[campaign_name] = new_data
            
            if not self.campaigns:
                logger.info("NO_CAMPAIGNS - No campaigns found")
                return
            
            credit_safe = self.check_credit_safety()
            current_time = datetime.now()
            
            for campaign_name, campaign_data in self.campaigns.items():
                top_bid = self.get_top_bid_from_bid_page(campaign_name)
                
                if top_bid:
                    old_top_bid = campaign_data.get('top_bid', 0)
                    campaign_data['top_bid'] = top_bid
                    campaign_data['last_checked'] = current_time
                    
                    # Update position
                    position = 1 if campaign_data['my_bid'] >= top_bid else 2
                    campaign_data['position'] = position
                    
                    # Check completion alerts (100% only)
                    self.check_completion_alerts(campaign_name, campaign_data)
                    
                    logger.info(f"CAMPAIGN_CHECK - {campaign_name} | Your: {campaign_data['my_bid']} | Top: {top_bid} | Position: #{position}")
                    
                    if credit_safe and campaign_data['auto_bid']:
                        self.execute_smart_auto_bid(campaign_name, campaign_data, top_bid)
                        
        except Exception as e:
            logger.error(f"CHECK_ALL_CAMPAIGNS_ERROR - {e}")

    def send_hourly_status(self):
        """Send automatic hourly status report"""
        if not self.campaigns and not self.market_bids:
            return
            
        traffic_credits = self.get_traffic_credits()
        visitor_credits = self.get_visitor_credits()
        
        status_msg = f"""
🕐 HOURLY STATUS REPORT

💰 CREDITS:
Traffic: {traffic_credits}
Visitors: {visitor_credits:,}

"""
        
        if self.campaigns:
            status_msg += "📊 YOUR CAMPAIGNS:\n"
            for name, data in self.campaigns.items():
                if 'views' in data:
                    views = data['views']
                    progress_pct = (views['current'] / views['total'] * 100) if views['total'] > 0 else 0
                    position = "🏆 #1" if data.get('my_bid', 0) >= data.get('top_bid', 0) else "📉 #2+"
                    status_msg += f"{position} \"{name}\" - {views['current']:,}/{views['total']:,} views ({progress_pct:.1f}%)\n"
        
        if self.market_bids:
            status_msg += f"\n🏪 MARKET:\nActive Campaigns: {len(self.market_bids)}\nBid Range: {min(self.market_bids.values())}-{max(self.market_bids.values())} credits\n"
        
        status_msg += "\n🤖 Bot is actively monitoring market + your campaigns..."
        
        self.send_telegram(status_msg)
        logger.info("HOURLY_STATUS_SENT - Automatic report delivered")

    def run(self):
        logger.info("BOT_INITIALIZING - Starting Ultimate Smart Bidder with Market Monitoring...")
        
        if not self.force_login():
            logger.error("BOT_START_FAILED - Initial login failed")
            return
        
        self.send_telegram("🚀 Ultimate Smart Bidder ACTIVATED!\nNow with 24/7 MARKET MONITORING! 📈\nType /help for commands")
        logger.info("BOT_STARTED - 24/7 monitoring + market scanning activated")
        
        last_command_check = 0
        last_campaign_check = 0
        last_market_check = 0
        last_hourly_status = time.time()
        last_health_check = time.time()
        
        while True:
            try:
                current_time = time.time()
                
                # Process Telegram commands every 3 seconds
                if current_time - last_command_check >= 3:
                    self.process_telegram_command()
                    last_command_check = current_time
                
                # Market scanning (every 5 minutes)
                if self.enable_market_alerts and current_time - last_market_check >= self.market_check_interval:
                    self.scan_market_bids()
                    last_market_check = current_time
                
                # Hourly status report (every 60 minutes)
                if current_time - last_hourly_status >= 3600:
                    if self.is_monitoring:
                        self.send_hourly_status()
                    last_hourly_status = current_time
                
                # Health check every 15 minutes
                if current_time - last_health_check >= 900:
                    if not self.smart_login():
                        logger.warning("HEALTH_CHECK_FAILED - Attempting re-login")
                        self.force_login()
                    last_health_check = current_time
                
                # Campaign checks every 3 minutes
                if self.is_monitoring:
                    if current_time - last_campaign_check >= self.check_interval:
                        self.check_all_campaigns()
                        last_campaign_check = current_time
                        logger.info(f"CHECK_CYCLE_COMPLETE - Next check in {self.check_interval//60}min")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"MAIN_LOOP_ERROR - {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = UltimateSmartBidder()
    bot.run()