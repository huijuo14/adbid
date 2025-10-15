import requests
from bs4 import BeautifulSoup
import time
import re
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class AdShareTracker:
    def __init__(self):
        self.current_bid = None
        self.bot_token = "8439342017:AAEmRrBp-AKzVK6cbRdHekDGSpbgi7aH5Nc"
        self.chat_id = "2052085789"
        self.session = requests.Session()
        self.email = "s.an.t.o.smaic.a36.9@gmail.com"
        self.password = "s.an.t.o.smaic.a36.9@gmail.com"
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
    def send_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
            response = self.session.post(url, data=data, timeout=30)
            if response.status_code == 200:
                logger.info("📱 Telegram sent")
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def login_to_adshare(self):
        try:
            login_url = "https://adsha.re/login"
            
            logger.info("🔐 Getting login page...")
            response = self.session.get(login_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to get login page: {response.status_code}")
                return False
            
            # Parse the form to get dynamic action URL and field names
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form', {'name': 'login'})
            
            if not form:
                logger.error("❌ Login form not found")
                return False
            
            # Get the dynamic action URL from the form
            action_url = form.get('action')
            if not action_url.startswith('http'):
                action_url = 'https://adsha.re' + action_url
            
            logger.info(f"🔐 Form action: {action_url}")
            
            # Prepare login data with CORRECT field names from HTML
            login_data = {
                'mail': self.email,  # Field name is 'mail' not 'email'
                '04ce63a75551c350478884bcd8e6530f': self.password  # Dynamic password field name
            }
            
            logger.info("🔐 Attempting login...")
            response = self.session.post(action_url, data=login_data, timeout=30, allow_redirects=True)
            
            # Check if login was successful by accessing protected page
            test_url = "https://adsha.re/adverts/create"
            response = self.session.get(test_url, timeout=30)
            
            if response.status_code == 200 and "adverts/create" in response.url:
                logger.info("✅ Login successful!")
                return True
            else:
                logger.error(f"❌ Login failed - Status: {response.status_code}, URL: {response.url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def get_top_bid(self):
        try:
            create_url = "https://adsha.re/adverts/create"
            
            logger.info("🔍 Fetching bid page...")
            response = self.session.get(create_url, timeout=30)
            
            # If redirected to login, session expired
            if response.status_code != 200 or "login" in response.url:
                logger.info("🔄 Session expired, re-logging in...")
                if self.login_to_adshare():
                    response = self.session.get(create_url, timeout=30)
                else:
                    return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for bid information
            for element in soup.find_all(string=re.compile(r'top bid is \d+ credits')):
                match = re.search(r'top bid is (\d+) credits', element)
                if match: 
                    bid = int(match.group(1))
                    logger.info(f"✅ Current bid: {bid} credits")
                    return bid
            
            # Alternative search
            labels = soup.find_all('div', class_='label')
            for label in labels:
                if 'top bid' in label.get_text():
                    match = re.search(r'(\d+) credits', label.get_text())
                    if match:
                        bid = int(match.group(1))
                        logger.info(f"✅ Found bid: {bid} credits")
                        return bid
            
            logger.warning("❌ Could not find bid information")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting bid: {e}")
            return None
    
    def start_tracking(self):
        logger.info("🚀 Starting AdShare Bid Tracker...")
        
        self.send_telegram("🤖 <b>AdShare Bid Tracker Starting...</b>")
        
        if not self.login_to_adshare():
            self.send_telegram("❌ <b>Login failed! Check credentials.</b>")
            return
        
        self.send_telegram("✅ <b>Login successful! Monitoring started.</b>")
        
        self.current_bid = self.get_top_bid()
        if self.current_bid:
            self.send_telegram(f"🎯 <b>Current Top Bid: {self.current_bid} credits</b>")
            logger.info(f"🎯 Initial bid: {self.current_bid} credits")
        else:
            self.send_telegram("❌ <b>Could not get initial bid</b>")
            return
        
        check_count = 0
        while True:
            try:
                time.sleep(300)
                check_count += 1
                
                logger.info(f"🔍 Check #{check_count}...")
                new_bid = self.get_top_bid()
                
                if new_bid and new_bid != self.current_bid:
                    logger.info(f"🚨 BID CHANGED: {self.current_bid} → {new_bid}")
                    
                    message = f"""🚨 <b>BID CHANGED!</b>

📊 Before: {self.current_bid} credits
📊 After: {new_bid} credits  
📈 Change: {new_bid - self.current_bid} credits
🕒 Time: {datetime.now().strftime('%H:%M:%S')}

🔗 https://adsha.re/adverts/create"""
                    
                    if self.send_telegram(message):
                        self.current_bid = new_bid
                
                elif new_bid:
                    logger.info(f"✅ No change: {new_bid} credits")
                    
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    tracker = AdShareTracker()
    tracker.start_tracking()
