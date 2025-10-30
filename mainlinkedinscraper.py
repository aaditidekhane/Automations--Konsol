import time
import random
import gspread
import pyperclip
from datetime import datetime, timedelta
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class LinkedInScraper:
    def __init__(self, google_sheets_key_file, sheet_name):
        print("🚀 Initializing Enhanced LinkedIn Scraper...")
        
        # Initialize Google Sheets
        try:
            self.gc = gspread.service_account(filename=google_sheets_key_file)
            self.sheet = self.gc.open(sheet_name).sheet1
            print("✅ Google Sheets connected successfully")
        except Exception as e:
            print(f"❌ Error connecting to Google Sheets: {e}")
            return
        
        # Setup enhanced Chrome options for better stealth
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--start-maximized")
        
        # Initialize Chrome driver
        try:
            service = Service("C:/chromedriver/chromedriver.exe")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Chrome browser initialized")
        except Exception as e:
            print(f"❌ Error initializing Chrome: {e}")
            print("Make sure ChromeDriver is installed at C:/chromedriver/chromedriver.exe")
            return
    
    def human_delay(self, min_seconds=1, max_seconds=2):
        """Reduced delay to mimic human behavior - max 2 seconds"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def human_scroll(self, element=None, scroll_type="smooth"):
        """Enhanced scrolling like a human would"""
        try:
            if element:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            else:
                # Fewer scrolls for faster processing
                for _ in range(random.randint(1, 2)):
                    scroll_distance = random.randint(150, 300)
                    self.driver.execute_script(f"window.scrollBy({{top: {scroll_distance}, behavior: 'smooth'}});")
                    self.human_delay(0.3, 0.6)
        except:
            pass
    
    def simulate_tab_switch(self):
        """Randomly simulate tab switching to avoid detection - reduced frequency"""
        if random.random() < 0.05:  # Reduced from 10% to 5% chance
            print("   🔄 Simulating tab switch...")
            # Open new tab and immediately close it
            self.driver.execute_script("window.open('');")
            self.human_delay(0.5, 1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.human_delay(0.5, 1)
    
    def human_mouse_move_and_click(self, element):
        """Enhanced mouse movement and clicking"""
        try:
            actions = ActionChains(self.driver)
            
            # Scroll element into view first
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            self.human_delay(0.3, 0.5)
            
            # Move to element with slight randomization
            actions.move_to_element_with_offset(element, 
                                              random.randint(-3, 3), 
                                              random.randint(-3, 3))
            actions.pause(random.uniform(0.2, 0.4))
            
            # Move to exact element
            actions.move_to_element(element)
            actions.pause(random.uniform(0.1, 0.3))
            
            # Click
            actions.click()
            actions.perform()
            
            self.human_delay(0.5, 0.8)
            return True
        except Exception as e:
            print(f"   ⚠️ Click failed: {e}")
            return False
    
    def extract_relative_date_text(self, post_container):
        """Extract the raw relative date text (3d, 1w, 2mo, etc.) from LinkedIn post"""
        try:
            # Enhanced selectors specifically for LinkedIn's relative date display
            date_selectors = [
                '.feed-shared-actor__sub-description time',
                '.feed-shared-actor__description time', 
                'time[datetime]',
                '.feed-shared-update-v2__actor-link time',
                '[data-test-id="main-feed-activity-card"] time',
                '.break-words time',
                '.feed-shared-actor__meta time',
                '.update-components-actor__meta time',
                '.feed-shared-text time'
            ]
            
            # Try each selector to find the date element
            for selector in date_selectors:
                try:
                    date_elements = post_container.find_elements(By.CSS_SELECTOR, selector)
                    for date_element in date_elements:
                        # Get the visible text which should contain relative date like "3d", "1w", "2mo"
                        date_text = date_element.text.strip()
                        if date_text:
                            # Clean and validate the relative date format
                            date_text = date_text.lower().replace('•', '').strip()
                            
                            # Check if it matches LinkedIn's relative date patterns
                            relative_patterns = [
                                r'\d+\s*m(?:in)?(?:ute)?s?',  # minutes: 5m, 30min, 45 minutes
                                r'\d+\s*h(?:our)?s?',         # hours: 2h, 5 hours  
                                r'\d+\s*d(?:ay)?s?',          # days: 3d, 5 days
                                r'\d+\s*w(?:eek)?s?',         # weeks: 1w, 2 weeks
                                r'\d+\s*mo(?:nth)?s?',        # months: 2mo, 3 months
                                r'\d+\s*y(?:ear)?s?',         # years: 1y, 2 years
                                r'now|just now',              # immediate
                            ]
                            
                            for pattern in relative_patterns:
                                if re.search(pattern, date_text):
                                    print(f"   📅 Found relative date: {date_text}")
                                    return date_text
                        
                        # Also check datetime attribute as fallback
                        datetime_attr = date_element.get_attribute('datetime')
                        if datetime_attr:
                            # If we have datetime but no visible text, try to convert to relative
                            try:
                                post_datetime = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                now = datetime.now(post_datetime.tzinfo) if post_datetime.tzinfo else datetime.now()
                                diff = now - post_datetime
                                
                                # Convert to LinkedIn-style relative format
                                if diff.days > 365:
                                    years = diff.days // 365
                                    return f"{years}y"
                                elif diff.days > 30:
                                    months = diff.days // 30
                                    return f"{months}mo"
                                elif diff.days > 7:
                                    weeks = diff.days // 7
                                    return f"{weeks}w"
                                elif diff.days > 0:
                                    return f"{diff.days}d"
                                elif diff.seconds > 3600:
                                    hours = diff.seconds // 3600
                                    return f"{hours}h"
                                elif diff.seconds > 60:
                                    minutes = diff.seconds // 60
                                    return f"{minutes}m"
                                else:
                                    return "now"
                            except:
                                continue
                                
                except Exception as e:
                    continue
            
            # If no relative date found, try broader search in the post container
            try:
                # Look for any text that matches relative date patterns in the entire post container
                container_text = post_container.text
                relative_patterns = [r'\b\d+\s*[mhdwMy]\b', r'\b\d+\s*mo\b', r'\bnow\b', r'\bjust now\b']
                
                for pattern in relative_patterns:
                    matches = re.findall(pattern, container_text, re.IGNORECASE)
                    if matches:
                        # Return the first match found
                        return matches[0].strip()
            except:
                pass
            
            return "Date not found"
            
        except Exception as e:
            print(f"   ⚠️ Error extracting relative date: {e}")
            return "Date extraction error"
    
    def is_post_recent_enough(self, relative_date_text):
        """Check if post is recent enough based on relative date text"""
        if not relative_date_text or relative_date_text in ["Date not found", "Date extraction error"]:
            return True  # Process if we can't determine age
        
        try:
            date_text = relative_date_text.lower().strip()
            
            # Immediate posts
            if any(term in date_text for term in ['now', 'just now']):
                return True
            
            # Extract number and unit
            numbers = re.findall(r'\d+', date_text)
            if not numbers:
                return True  # Default to processing if can't parse
            
            value = int(numbers[0])
            
            # Check based on time unit
            if 'm' in date_text and 'mo' not in date_text:  # minutes
                return True
            elif 'h' in date_text:  # hours
                return True
            elif 'd' in date_text:  # days
                return value <= 30
            elif 'w' in date_text:  # weeks
                return value <= 4  # ~30 days
            elif 'mo' in date_text:  # months
                return value <= 1
            elif 'y' in date_text:  # years
                return False
            
            return True  # Default to processing
            
        except:
            return True  # Default to processing if parsing fails
    
    def login_to_linkedin(self):
        """Manual login process with enhanced verification"""
        print("\n🔐 Starting LinkedIn login process...")
        self.driver.get("https://www.linkedin.com/login")
        self.driver.maximize_window()
        
        print("👆 Please log in manually in the browser window...")
        print("   1. Enter your email and password")
        print("   2. Complete any 2FA if required")
        print("   3. Make sure you're on your LinkedIn homepage")
        
        input("\n⏳ Press Enter after you've successfully logged in...")
        
        # Enhanced login verification
        current_url = self.driver.current_url
        if any(keyword in current_url for keyword in ["feed", "linkedin.com/in/", "mynetwork", "messaging"]):
            print("✅ Login successful!")
            self.human_delay(1, 2)  # Reduced delay
            return True
        else:
            print("❌ Login may have failed. Please try again.")
            return False
    
    def get_linkedin_urls_from_sheet(self):
        """Get all LinkedIn URLs from the sheet with enhanced error handling"""
        print("\n📊 Reading data from Google Sheet...")
        try:
            records = self.sheet.get_all_records()
            valid_records = [r for r in records if r.get('Linkedin Url', '').strip()]
            print(f"✅ Found {len(valid_records)} profiles to scrape")
            return valid_records
        except Exception as e:
            print(f"❌ Error reading sheet: {e}")
            return []
    
    def expand_post_content(self):
        """Click 'see more' or '...more' buttons to expand full post content"""
        try:
            see_more_selectors = [
                'button[aria-label*="see more"]',
                'button:contains("see more")',
                'button:contains("...more")',
                '.feed-shared-inline-show-more-text button',
                '[data-test-id="see-more-button"]',
                'button[aria-expanded="false"]:contains("more")',
                '.see-more',
                'button.see-more'
            ]
            
            # Use XPath for better text matching
            see_more_xpath_selectors = [
                "//button[contains(text(), 'see more')]",
                "//button[contains(text(), '...more')]",
                "//button[contains(@aria-label, 'see more')]",
                "//span[contains(text(), 'see more')]/parent::button",
                "//*[contains(text(), 'see more') and (self::button or self::span)]"
            ]
            
            expanded = False
            
            # Try XPath selectors first
            for xpath in see_more_xpath_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements[:2]:  # Try first 2 matches
                        if element.is_displayed() and element.is_enabled():
                            print("   🔍 Found 'see more' button, expanding post...")
                            self.human_scroll(element)
                            if self.human_mouse_move_and_click(element):
                                self.human_delay(1, 1.5)  # Reduced delay
                                expanded = True
                                break
                    if expanded:
                        break
                except:
                    continue
            
            # Try CSS selectors as fallback
            if not expanded:
                for selector in see_more_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements[:2]:
                            if element.is_displayed() and element.is_enabled():
                                print("   🔍 Found 'see more' button (CSS), expanding post...")
                                self.human_scroll(element)
                                if self.human_mouse_move_and_click(element):
                                    self.human_delay(1, 1.5)  # Reduced delay
                                    expanded = True
                                    break
                        if expanded:
                            break
                    except:
                        continue
            
            if expanded:
                print("   ✅ Post content expanded")
            
            return expanded
            
        except Exception as e:
            print(f"   ⚠️ Error expanding post: {e}")
            return False
    
    def extract_post_content_enhanced(self):
        """Enhanced post content extraction with relative date extraction"""
        try:
            print("   🔍 Looking for post content...")
            
            # Reduced wait time for posts to load
            self.human_delay(2, 3)
            
            # Look for the first post container
            post_selectors = [
                '[data-test-id="main-feed-activity-card"]',
                '.feed-shared-update-v2',
                '[data-urn*="activity"]',
                '.feed-shared-card-v2',
                '.feed-shared-update-v2__content'
            ]
            
            post_container = None
            for selector in post_selectors:
                try:
                    posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if posts:
                        post_container = posts[0]
                        print(f"   ✅ Found post container with: {selector}")
                        break
                except:
                    continue
            
            if not post_container:
                return {"content": "No posts found on this profile", "relative_date": "No date found"}
            
            # Scroll to the post
            self.human_scroll(post_container)
            self.human_delay(0.5, 1)  # Reduced delay
            
            # Extract relative date text (3d, 1w, 2mo, etc.)
            relative_date = self.extract_relative_date_text(post_container)
            
            # Check if post is recent enough
            if not self.is_post_recent_enough(relative_date):
                return {
                    "content": f"Post is older than 30 days ({relative_date})",
                    "relative_date": relative_date,
                    "within_30_days": False
                }
            
            # Try to expand the post content first
            self.expand_post_content()
            self.human_delay(0.5, 1)  # Reduced delay
            
            # Enhanced content selectors for full post content
            content_selectors = [
                '.feed-shared-update-v2__commentary .break-words',
                '.feed-shared-update-v2__description .break-words',
                '.feed-shared-text .break-words',
                '.feed-shared-update-v2__description-wrapper',
                '.feed-shared-inline-show-more-text',
                '[data-test-id="main-feed-activity-card"] .break-words',
                '.update-components-text .break-words span'
            ]
            
            post_text_element = None
            best_content = ""
            
            # Try all selectors and get the longest content
            for selector in content_selectors:
                try:
                    elements = post_container.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.text.strip() and len(element.text.strip()) > len(best_content):
                            post_text_element = element
                            best_content = element.text.strip()
                except:
                    continue
            
            if not post_text_element or len(best_content) < 5:
                return {
                    "content": "Post found but content is private or unavailable",
                    "relative_date": relative_date,
                    "within_30_days": True
                }
            
            # Enhanced content copying with reduced delays
            print("   🖱️ Selecting and copying post content...")
            
            # Clear clipboard
            pyperclip.copy("")
            self.human_delay(0.3, 0.5)  # Reduced delay
            
            # Multiple selection strategies
            success = False
            
            # Strategy 1: Triple click to select paragraph
            try:
                self.human_mouse_move_and_click(post_text_element)
                actions = ActionChains(self.driver)
                for _ in range(3):
                    actions.click(post_text_element)
                    actions.pause(0.1)  # Reduced pause
                actions.perform()
                
                # Copy selected text
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
                self.human_delay(0.5, 1)  # Reduced delay
                
                copied_content = pyperclip.paste().strip()
                if copied_content and len(copied_content) > 10:
                    success = True
                    best_content = copied_content
            except:
                pass
            
            # Strategy 2: Select all text in element using JavaScript
            if not success:
                try:
                    self.driver.execute_script("""
                        var element = arguments[0];
                        var range = document.createRange();
                        range.selectNodeContents(element);
                        var selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                    """, post_text_element)
                    
                    self.human_delay(0.3, 0.5)  # Reduced delay
                    
                    # Copy selected text
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
                    self.human_delay(0.5, 1)  # Reduced delay
                    
                    copied_content = pyperclip.paste().strip()
                    if copied_content and len(copied_content) > 10:
                        success = True
                        best_content = copied_content
                except:
                    pass
            
            # Strategy 3: Use element.text as fallback
            if not success:
                best_content = post_text_element.text.strip()
            
            if best_content and len(best_content) > 5:
                print(f"   ✅ Extracted post content: {best_content[:100]}...")
                return {
                    "content": best_content,
                    "relative_date": relative_date,
                    "within_30_days": True
                }
            else:
                return {
                    "content": "Could not extract post content",
                    "relative_date": relative_date,
                    "within_30_days": True
                }
                
        except Exception as e:
            print(f"   ❌ Error extracting post: {e}")
            return {
                "content": f"Error extracting post: {str(e)}",
                "relative_date": "Error",
                "within_30_days": True
            }
    
    def get_post_url_enhanced(self):
        """Enhanced post URL extraction with reduced delays"""
        try:
            print("   🔗 Getting post URL...")
            
            # Try direct post link first
            post_link_selectors = [
                '[data-test-id="main-feed-activity-card"] a[href*="/posts/"]',
                '.feed-shared-update-v2 a[href*="/posts/"]',
                'a[href*="/posts/activity-"]',
                '[href*="linkedin.com/posts/"]'
            ]
            
            for selector in post_link_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if links:
                        post_url = links[0].get_attribute('href')
                        print(f"   ✅ Found direct post URL")
                        return post_url
                except:
                    continue
            
            # Fallback: Try three dots menu method
            three_dots_selectors = [
                'button[aria-label*="more"]',
                'button[data-test-id="more-menu-trigger"]',
                'button[aria-label*="Open control menu"]',
                'button[aria-label*="More actions"]'
            ]
            
            for selector in three_dots_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        button = buttons[0]
                        self.human_scroll(button)
                        if self.human_mouse_move_and_click(button):
                            self.human_delay(1, 1.5)  # Reduced delay
                            
                            # Look for copy link option
                            copy_link_xpath = "//span[contains(text(), 'Copy link to post')] | //div[contains(text(), 'Copy link')]"
                            try:
                                copy_elements = self.driver.find_elements(By.XPATH, copy_link_xpath)
                                if copy_elements:
                                    if self.human_mouse_move_and_click(copy_elements[0]):
                                        self.human_delay(0.5, 1)  # Reduced delay
                                        copied_url = pyperclip.paste().strip()
                                        if copied_url and 'linkedin.com' in copied_url:
                                            return copied_url
                            except:
                                pass
                            
                            # Close menu
                            self.driver.find_element(By.TAG_NAME, "body").click()
                            break
                except:
                    continue
            
            # Final fallback
            return self.driver.current_url
            
        except Exception as e:
            print(f"   ⚠️ Error getting post URL: {e}")
            return self.driver.current_url
    
    def scrape_recent_post_enhanced(self, linkedin_url):
        """Enhanced scraping with relative date extraction and reduced delays"""
        print(f"🔍 Scraping: {linkedin_url}")
        
        try:
            # Clean URL and navigate
            profile_url = linkedin_url.rstrip('/')
            activity_url = f"{profile_url}/recent-activity/all/"
            
            print(f"   🌐 Navigating to activity page...")
            self.driver.get(activity_url)
            
            # Reduced waiting and loading
            WebDriverWait(self.driver, 15).until(  # Reduced from 20 to 15
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            
            # Simulate human-like page interaction with reduced delays
            self.human_delay(2, 3)  # Reduced from 4-7 to 2-3
            self.human_scroll()
            self.human_delay(1, 2)  # Reduced from 2-4 to 1-2
            
            # Random tab switch simulation (reduced frequency)
            self.simulate_tab_switch()
            
            # Extract post content with enhanced method
            post_data = self.extract_post_content_enhanced()
            
            # Skip old posts
            if post_data.get("within_30_days") == False:
                print(f"   ⏰ Skipping old post: {post_data['relative_date']}")
                return post_data
            
            # Get post URL
            post_url = self.get_post_url_enhanced()
            post_data["url"] = post_url
            
            # If content extraction failed from activity page, try main profile
            if (post_data["content"] in ["No posts found on this profile", 
                                       "Post found but content is private or unavailable",
                                       "Could not extract post content"] or 
                len(post_data["content"].strip()) < 15):
                
                print("   🔄 Trying main profile page...")
                self.driver.get(profile_url)
                
                self.human_delay(3, 4)  # Reduced from 5-8 to 3-4
                self.human_scroll()
                self.human_delay(1, 2)  # Reduced from 3-5 to 1-2
                
                main_profile_data = self.extract_post_content_enhanced()
                if (main_profile_data["content"] and 
                    len(main_profile_data["content"].strip()) > len(post_data["content"].strip())):
                    post_data = main_profile_data
                    post_data["url"] = self.get_post_url_enhanced()
            
            return post_data
            
        except Exception as e:
            error_msg = f"Error accessing profile: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "content": error_msg,
                "relative_date": "Error",
                "url": linkedin_url,
                "within_30_days": True
            }
    
    def setup_sheet_columns(self):
        """Setup sheet columns including the relative date column"""
        try:
            # Get current headers
            headers = self.sheet.row_values(1)
            
            # Define expected headers (changed "Post Date" to "Relative Date")
            expected_headers = ['First Name', 'Last Name', 'Linkedin Url', 'Post Content', 'Post URL', 'Relative Date']
            
            # Check if we need to add headers
            if len(headers) < len(expected_headers):
                print("📝 Setting up sheet columns...")
                # Update the header row
                self.sheet.update('A1:F1', [expected_headers])
                print("✅ Sheet headers updated")
                
        except Exception as e:
            print(f"⚠️ Error setting up columns: {e}")
    
    def update_sheet_with_enhanced_data(self, row_index, post_data):
        """Update Google Sheet with all extracted data including relative date"""
        try:
            content = str(post_data.get('content', 'No content found'))[:2000]
            url = str(post_data.get('url', 'No URL available'))
            relative_date = post_data.get('relative_date', 'No date found')
            
            print(f"   📝 Updating sheet row {row_index}...")
            
            # Update columns D, E, and F (Post Content, Post URL, Relative Date)
            self.sheet.update(f'D{row_index}', [[content]])
            time.sleep(1)  # Reduced from 1.5
            self.sheet.update(f'E{row_index}', [[url]])
            time.sleep(1)  # Reduced from 1.5
            self.sheet.update(f'F{row_index}', [[relative_date]])
            
            print(f"   ✅ Updated row {row_index} with content, URL, and relative date")
            time.sleep(1)  # Reduced from 2 - API rate limit protection
            
        except Exception as e:
            print(f"   ❌ Error updating sheet: {str(e)}")
    
    def scrape_all_profiles_optimized(self):
        """Optimized scraping with reduced delays"""
        # Setup sheet columns
        self.setup_sheet_columns()
        
        records = self.get_linkedin_urls_from_sheet()
        
        if not records:
            print("❌ No valid LinkedIn URLs found in sheet")
            return
        
        print(f"\n🚀 Starting optimized scraping for {len(records)} profiles...")
        print("⏰ Estimated time: ~25-35 minutes for 130 profiles (with reduced delays)")
        
        start_time = time.time()
        successful = 0
        skipped_old = 0
        errors = 0
        
        for index, record in enumerate(records):
            linkedin_url = record.get('Linkedin Url', '').strip()
            first_name = record.get('First Name', 'Unknown')
            last_name = record.get('Last Name', 'User')
            
            print(f"\n[{index + 1}/{len(records)}] Processing: {first_name} {last_name}")
            
            try:
                # Scrape the post
                post_data = self.scrape_recent_post_enhanced(linkedin_url)
                
                # Update sheet
                self.update_sheet_with_enhanced_data(index + 2, post_data)
                
                # Track statistics
                if post_data.get("within_30_days") == False:
                    skipped_old += 1
                    print(f"   ⏰ Post older than 30 days - skipped ({post_data.get('relative_date', 'unknown')})")
                elif "Error" in post_data.get("content", ""):
                    errors += 1
                else:
                    successful += 1
                
                # Optimized delays - REDUCED to 12-16 seconds max
                if index < len(records) - 1:  # Don't delay after last profile
                    delay = random.randint(12, 16)  # Reduced from 15-25 to 12-16 seconds
                    print(f"   ⏳ Waiting {delay} seconds before next profile...")
                    time.sleep(delay)
                
                # Progress update every 10 profiles
                if (index + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time_per_profile = elapsed / (index + 1)
                    remaining_profiles = len(records) - (index + 1)
                    estimated_remaining = (remaining_profiles * avg_time_per_profile) / 60
                    
                    print(f"\n📊 Progress Update:")
                    print(f"   Completed: {index + 1}/{len(records)} profiles")
                    print(f"   Successful: {successful}, Skipped (old): {skipped_old}, Errors: {errors}")
                    print(f"   Estimated time remaining: {estimated_remaining:.1f} minutes\n")
                
            except KeyboardInterrupt:
                print("\n⚠️ Scraping interrupted by user")
                break
            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
                errors += 1
        
        # Final statistics
        total_time = (time.time() - start_time) / 60
        print(f"\n🎉 Scraping completed!")
        print(f"📊 Final Statistics:")
        print(f"   Total profiles processed: {index + 1}")
        print(f"   Successful: {successful}")
        print(f"   Skipped (older than 30 days): {skipped_old}")
        print(f"   Errors: {errors}")
        print(f"   Total time: {total_time:.1f} minutes")
        print(f"   Average time per profile: {(total_time * 60) / (index + 1):.1f} seconds")
    
    def close(self):
        """Enhanced cleanup"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                print("✅ Browser closed successfully")
            except:
                pass

# Main execution
if __name__ == "__main__":
    print("🚀 Enhanced LinkedIn Post Scraper Starting...")
    print("=" * 60)
    print("🔹 Features: Relative date extraction (3d, 1w, 2mo), full content reading")
    print("🔹 Optimized delays: 12-16 seconds between profiles")
    print("🔹 Extracts LinkedIn's native relative dates instead of converting to absolute dates")
    print("=" * 60)
    
    # Configuration - UPDATE THESE PATHS!
    CREDENTIALS_FILE = "C:/Users/aditi/OneDrive/Desktop/credentials.json"
    SHEET_NAME = "linkedin_contacts"
    
    try:
        # Initialize enhanced scraper
        scraper = LinkedInScraper(
            google_sheets_key_file=CREDENTIALS_FILE,
            sheet_name=SHEET_NAME
        )
        
        print("\n📋 Pre-scraping checklist:")
        print("   ✓ Chrome browser will open automatically")
        print("   ✓ You'll need to login manually (one time)")
        print("   ✓ Script will handle profiles with reduced delays (12-16s)")
        print("   ✓ Only posts within 1 MONTH will be processed (strict filter)")
        print("   ✓ Extracts relative dates like '3d', '1w', '25d' from LinkedIn")
        print("   ✓ Full post content will be extracted (expanding 'see more')")
        
        # Login to LinkedIn
        if scraper.login_to_linkedin():
            print("\n🎯 Starting optimized scraping process...")
            scraper.scrape_all_profiles_optimized()
        else:
            print("❌ Login failed. Please try again.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always clean up
        if 'scraper' in locals():
            scraper.close()
    
    print("\n✅ Enhanced LinkedIn Scraper completed!")
    print("📊 Check your Google Sheet for updated data with relative dates")
    input("Press Enter to exit...")


# Additional utility functions for advanced users

def batch_process_urls(url_list, credentials_file, sheet_name, start_index=0):
    """
    Process a specific batch of URLs - useful for resuming interrupted scraping
    
    Args:
        url_list: List of LinkedIn URLs to process
        credentials_file: Path to Google credentials JSON
        sheet_name: Name of the Google Sheet
        start_index: Index to start processing from (for resuming)
    """
    scraper = None
    try:
        scraper = LinkedInScraper(credentials_file, sheet_name)
        if not scraper.login_to_linkedin():
            return False
        
        for i, url in enumerate(url_list[start_index:], start_index):
            print(f"Processing {i+1}/{len(url_list)}: {url}")
            post_data = scraper.scrape_recent_post_enhanced(url)
            scraper.update_sheet_with_enhanced_data(i + 2, post_data)
            
            if i < len(url_list) - 1:
                time.sleep(random.randint(12, 16))  # Reduced delay
        
        return True
    except Exception as e:
        print(f"Batch processing error: {e}")
        return False
    finally:
        if scraper:
            scraper.close()

def validate_linkedin_urls(sheet_path):
    """
    Validate LinkedIn URLs in the sheet before scraping
    
    Args:
        sheet_path: Path to Google credentials JSON
    """
    try:
        gc = gspread.service_account(filename=sheet_path)
        sheet = gc.open("linkedin_contacts").sheet1
        records = sheet.get_all_records()
        
        valid_urls = []
        invalid_urls = []
        
        for i, record in enumerate(records):
            url = record.get('Linkedin Url', '').strip()
            if url:
                if 'linkedin.com/in/' in url:
                    valid_urls.append((i+2, url))  # +2 for header row
                else:
                    invalid_urls.append((i+2, url))
        
        print(f"✅ Valid URLs: {len(valid_urls)}")
        print(f"❌ Invalid URLs: {len(invalid_urls)}")
        
        if invalid_urls:
            print("\nInvalid URLs found:")
            for row, url in invalid_urls[:5]:  # Show first 5
                print(f"   Row {row}: {url}")
        
        return valid_urls, invalid_urls
    
    except Exception as e:
        print(f"Validation error: {e}")
        return [], []

# Performance monitoring with updated timing
class PerformanceMonitor:
    """Monitor scraping performance and provide insights"""
    
    def __init__(self):
        self.start_time = time.time()
        self.profile_times = []
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0
    
    def log_profile(self, success=True, error=False, skipped=False):
        current_time = time.time()
        self.profile_times.append(current_time)
        
        if success:
            self.success_count += 1
        elif error:
            self.error_count += 1
        elif skipped:
            self.skip_count += 1
    
    def get_stats(self):
        if not self.profile_times:
            return "No data yet"
        
        total_time = time.time() - self.start_time
        avg_time_per_profile = total_time / len(self.profile_times)
        
        return {
            "total_time_minutes": total_time / 60,
            "profiles_processed": len(self.profile_times),
            "avg_time_per_profile": avg_time_per_profile,
            "success_rate": (self.success_count / len(self.profile_times)) * 100,
            "estimated_completion": avg_time_per_profile * (130 - len(self.profile_times)) / 60
        }