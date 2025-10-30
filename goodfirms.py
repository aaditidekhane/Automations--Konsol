"""
GoodFirms Human-Like Scraper - FIXED VERSION
This version fixes:
1. Column header and data mismatch
2. Duplicate reviewers and redundant data
3. Proper mapping of data from website to sheet
4. Regex syntax errors
5. Correct data mapping in sheet

Requirements:
pip install playwright pandas openpyxl
playwright install chromium
"""

import asyncio
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple

import pandas as pd
from playwright.async_api import async_playwright, Page, Locator


class HumanLikeGoodFirmsScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.data = []
        self.delay = 2
        self.seen_reviews: Set[Tuple[str, str, str]] = set()  # Track unique reviews
        
    async def extract_company_urls(self, page: Page, max_companies: int = 10) -> List[str]:
        """Extract company URLs from listing page"""
        print(f"🔍 Loading: {self.base_url}\n")
        
        await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        
        # Scroll to load all companies
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)
        
        print("📋 Extracting company URLs...\n")
        
        # Get all company profile links
        company_links = await page.evaluate("""
            () => {
                const links = new Set();
                
                // Look for company profile links
                document.querySelectorAll('a').forEach(a => {
                    const href = a.href;
                    if (href && 
                        href.includes('goodfirms.co/company/') && 
                        !href.includes('#') && 
                        !href.includes('?')) {
                        links.add(href);
                    }
                });
                
                return Array.from(links);
            }
        """)
        
        company_links = list(company_links)[:max_companies]
        
        print(f"✅ Found {len(company_links)} companies to scrape\n")
        
        for i, url in enumerate(company_links[:5], 1):
            print(f"   {i}. {url.split('/')[-1]}")
        
        if len(company_links) > 5:
            print(f"   ... and {len(company_links) - 5} more\n")
        
        return company_links
    
    async def human_like_scroll(self, page: Page):
        """Scroll page like a human to load all content"""
        # Scroll down gradually
        for i in range(5):
            await page.evaluate(f"window.scrollBy(0, {300 + i * 100})")
            await asyncio.sleep(0.5)
        
        # Scroll back up
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        
        # Final scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
    
    async def extract_text_safely(self, page: Page, selector: str, multiple: bool = False) -> Any:
        """Extract text using multiple fallback strategies"""
        try:
            if multiple:
                elements = await page.query_selector_all(selector)
                return [await el.inner_text() for el in elements if el]
            else:
                element = await page.query_selector(selector)
                if element:
                    return await element.inner_text()
        except:
            pass
        return [] if multiple else ''
    
    async def extract_company_details(self, page: Page, url: str, index: int, total: int) -> Dict[str, Any]:
        """Extract company details with human-like behavior"""
        print(f"[{index}/{total}] 🏢 {url.split('/')[-1][:50]}")
        
        try:
            # Navigate like a human
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            # Scroll to load content
            await self.human_like_scroll(page)
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Extract all visible text content in structured way
            company_data = await page.evaluate("""
                () => {
                    // Helper function to get clean text
                    const getCleanText = (element) => {
                        if (!element) return '';
                        return element.innerText?.trim() || element.textContent?.trim() || '';
                    };
                    
                    // Helper to parse "Name, Position at Company" into separate fields
                    const parseReviewerInfo = (text) => {
                        const result = {
                            name: '',
                            position: '',
                            company: ''
                        };
                        
                        if (!text) return result;
                        
                        // Clean the text first
                        text = text.trim();
                        
                        // Pattern 1: "John Doe, CEO at Company Name"
                        const atPattern = /^([^,]+),\\s*(.+?)\\s+at\\s+(.+)$/i;
                        let match = text.match(atPattern);
                        if (match) {
                            result.name = match[1].trim();
                            result.position = match[2].trim();
                            result.company = match[3].trim();
                            return result;
                        }
                        
                        // Pattern 2: "John Doe | CEO | Company Name"
                        const parts = text.split('|').map(p => p.trim()).filter(p => p);
                        if (parts.length >= 3) {
                            result.name = parts[0];
                            result.position = parts[1];
                            result.company = parts[2];
                            return result;
                        }
                        
                        // Pattern 3: "John Doe, CEO, Company Name"
                        const commaParts = text.split(',').map(p => p.trim()).filter(p => p);
                        if (commaParts.length >= 3) {
                            result.name = commaParts[0];
                            result.position = commaParts[1];
                            result.company = commaParts[2];
                            return result;
                        } else if (commaParts.length === 2) {
                            result.name = commaParts[0];
                            result.position = commaParts[1];
                            return result;
                        } else if (commaParts.length === 1) {
                            result.name = commaParts[0];
                            return result;
                        }
                        
                        // Pattern 4: Try newline separation
                        const linePattern = /\\r?\\n/;
                        const lineParts = text.split(linePattern).map(p => p.trim()).filter(p => p);
                        if (lineParts.length >= 3) {
                            result.name = lineParts[0];
                            result.position = lineParts[1];
                            result.company = lineParts[2];
                            return result;
                        } else if (lineParts.length === 2) {
                            result.name = lineParts[0];
                            result.position = lineParts[1];
                            return result;
                        } else if (lineParts.length === 1) {
                            result.name = lineParts[0];
                            return result;
                        }
                        
                        // Default: just use as name
                        result.name = text;
                        return result;
                    };
                    
                    const data = {
                        companyName: '',
                        website: '',
                        location: '',
                        employeeSize: '',
                        services: [],
                        reviews: []
                    };
                    
                    // Extract company name
                    const nameSelectors = [
                        'h1.profile-header__title',
                        'h1[class*="company-name"]',
                        'h1[class*="profile"]',
                        '.company-profile h1',
                        'h1'
                    ];
                    
                    for (const selector of nameSelectors) {
                        const element = document.querySelector(selector);
                        if (element && getCleanText(element)) {
                            data.companyName = getCleanText(element);
                            break;
                        }
                    }
                    
                    // Extract website
                    const websiteLink = document.querySelector('a[href*="http"][target="_blank"]') ||
                                      document.querySelector('a[class*="website"]');
                    if (websiteLink) {
                        data.website = websiteLink.href || '';
                    }
                    
                    // Extract location
                    const locationSelectors = [
                        '[class*="location"]',
                        '[class*="address"]',
                        'span:has(svg[class*="location"])',
                        'div:has(svg[class*="map"])'
                    ];
                    
                    for (const selector of locationSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const text = getCleanText(element);
                            if (text && text.length > 2 && text.length < 100) {
                                data.location = text;
                                break;
                            }
                        }
                    }
                    
                    // Extract employee size
                    const employeeSizeSelectors = [
                        '[class*="employee"]',
                        '[class*="team-size"]',
                        'span:has-text("Employees")',
                        'div:has-text("Team Size")'
                    ];
                    
                    for (const selector of employeeSizeSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const text = getCleanText(element);
                            const sizePattern = /\d+\s*-\s*\d+|\d+\+|<\s*\d+|>\s*\d+/;
                            if (sizePattern.test(text)) {
                                data.employeeSize = text.match(sizePattern)[0];
                                break;
                            }
                        }
                    }
                    
                    // Extract services
                    const serviceElements = document.querySelectorAll('[class*="service"], [class*="expertise"], .tag, .badge');
                    const services = new Set();
                    serviceElements.forEach(el => {
                        const text = getCleanText(el);
                        if (text && text.length > 2 && text.length < 100 && !text.includes('View') && !text.includes('More')) {
                            services.add(text);
                        }
                    });
                    data.services = Array.from(services);
                    
                    // Extract reviews - IMPROVED EXTRACTION
                    const reviewElements = document.querySelectorAll('[class*="review"], [class*="testimonial"], [class*="feedback"]');
                    const processedReviews = new Set(); // Track unique reviews
                    
                    reviewElements.forEach(reviewEl => {
                        const review = {
                            reviewerName: '',
                            reviewerPosition: '',
                            reviewerCompany: '',
                            reviewerLocation: '',
                            reviewerIndustry: '',
                            reviewText: '',
                            rating: '',
                            service: '',
                            projectSummary: '',
                            startDate: '',
                            budget: ''
                        };
                        
                        // Extract reviewer information - multiple strategies
                        const reviewerSelectors = [
                            '[class*="reviewer-name"]',
                            '[class*="client-name"]',
                            '[class*="author"]',
                            'h3',
                            'h4',
                            '.name',
                            'strong'
                        ];
                        
                        let reviewerFound = false;
                        for (const selector of reviewerSelectors) {
                            const reviewerEl = reviewEl.querySelector(selector);
                            if (reviewerEl) {
                                const reviewerText = getCleanText(reviewerEl);
                                if (reviewerText && reviewerText.length > 2 && reviewerText.length < 200) {
                                    const parsed = parseReviewerInfo(reviewerText);
                                    review.reviewerName = parsed.name;
                                    review.reviewerPosition = parsed.position;
                                    review.reviewerCompany = parsed.company;
                                    reviewerFound = true;
                                    break;
                                }
                            }
                        }
                        
                        // Skip if no reviewer name found
                        if (!reviewerFound || !review.reviewerName) {
                            return;
                        }
                        
                        // Extract location
                        const locationEl = reviewEl.querySelector('[class*="location"], [class*="country"]');
                        if (locationEl) {
                            review.reviewerLocation = getCleanText(locationEl);
                        }
                        
                        // Extract industry
                        const industryEl = reviewEl.querySelector('[class*="industry"], [class*="sector"]');
                        if (industryEl) {
                            review.reviewerIndustry = getCleanText(industryEl);
                        }
                        
                        // Extract review text
                        const reviewTextSelectors = [
                            '[class*="review-text"]',
                            '[class*="review-content"]',
                            '[class*="feedback-text"]',
                            'p',
                            '.content'
                        ];
                        
                        for (const selector of reviewTextSelectors) {
                            const textEl = reviewEl.querySelector(selector);
                            if (textEl) {
                                const text = getCleanText(textEl);
                                if (text && text.length > 20) {
                                    review.reviewText = text;
                                    break;
                                }
                            }
                        }
                        
                        // Extract rating
                        const ratingEl = reviewEl.querySelector('[class*="rating"], [class*="star"], [class*="score"]');
                        if (ratingEl) {
                            const ratingText = getCleanText(ratingEl);
                            const ratingPattern = /\d+\.?\d*/;
                            const ratingMatch = ratingText.match(ratingPattern);
                            if (ratingMatch) {
                                review.rating = ratingMatch[0];
                            }
                        }
                        
                        // Extract service
                        const serviceEl = reviewEl.querySelector('[class*="service"], [class*="category"]');
                        if (serviceEl) {
                            review.service = getCleanText(serviceEl);
                        }
                        
                        // Extract project summary
                        const summaryEl = reviewEl.querySelector('[class*="project"], [class*="summary"]');
                        if (summaryEl) {
                            review.projectSummary = getCleanText(summaryEl);
                        }
                        
                        // Extract start date
                        const dateEl = reviewEl.querySelector('[class*="date"], [class*="time"]');
                        if (dateEl) {
                            const dateText = getCleanText(dateEl);
                            const datePattern = /\d{4}|\d{1,2}\/\d{1,2}\/\d{2,4}|[A-Z][a-z]+\s+\d{4}/;
                            const dateMatch = dateText.match(datePattern);
                            if (dateMatch) {
                                review.startDate = dateMatch[0];
                            }
                        }
                        
                        // Extract budget
                        const budgetEl = reviewEl.querySelector('[class*="budget"], [class*="cost"], [class*="price"]');
                        if (budgetEl) {
                            const budgetText = getCleanText(budgetEl);
                            const budgetPattern = /\$[\d,]+\s*-?\s*\$?[\d,]*|\$[\d,]+\+?/;
                            const budgetMatch = budgetText.match(budgetPattern);
                            if (budgetMatch) {
                                review.budget = budgetMatch[0];
                            }
                        }
                        
                        // Create unique identifier for this review
                        const reviewKey = `${review.reviewerName}|${review.reviewText.substring(0, 50)}|${review.rating}`;
                        
                        // Only add if we have a name and haven't seen this review before
                        if (review.reviewerName && !processedReviews.has(reviewKey)) {
                            processedReviews.add(reviewKey);
                            data.reviews.push(review);
                        }
                    });
                    
                    return data;
                }
            """)
            
            # Add URL to data
            company_data['companyUrl'] = url
            
            # Print summary with debugging info
            review_count = len(company_data['reviews'])
            
            if review_count > 0:
                print(f"   ✅ Found {review_count} unique named review(s)")
                # Show first reviewer name for verification
                if company_data['reviews']:
                    first_name = company_data['reviews'][0].get('reviewerName', 'N/A')
                    print(f"      Example: {first_name[:50]}")
            else:
                print(f"   ℹ️  No valid named reviews found")
            
            return company_data
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:80]}")
            return None
    
    def is_duplicate_review(self, company_name: str, reviewer_name: str, review_text: str) -> bool:
        """Check if a review is a duplicate"""
        # Create a unique key from company, reviewer, and part of review text
        review_key = (
            company_name.lower().strip(),
            reviewer_name.lower().strip(),
            review_text[:100].lower().strip()  # First 100 chars
        )
        
        if review_key in self.seen_reviews:
            return True
        
        self.seen_reviews.add(review_key)
        return False
    
    async def scrape(self, max_companies: int = 10, headless: bool = False):
        """Main scraping process"""
        print("=" * 80)
        print("  🤖 GoodFirms Human-Like Scraper - FIXED VERSION")
        print("=" * 80)
        print(f"  Target: {self.base_url}")
        print(f"  Max companies: {max_companies}")
        print(f"  Headless: {headless}")
        print("=" * 80)
        print()
        
        start_time = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=['--start-maximized']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Phase 1: Get company URLs
            print("📋 PHASE 1: Collecting Company URLs\n")
            company_urls = await self.extract_company_urls(page, max_companies)
            
            if not company_urls:
                print("❌ No companies found. Exiting.")
                await browser.close()
                return
            
            print()
            print("=" * 80)
            print(f"📊 PHASE 2: Extracting Data from {len(company_urls)} Companies")
            print("=" * 80)
            print()
            
            # Phase 2: Extract data from each company
            for idx, company_url in enumerate(company_urls, 1):
                company_data = await self.extract_company_details(page, company_url, idx, len(company_urls))
                
                if company_data:
                    reviews = company_data.pop('reviews', [])
                    
                    # Reviews are already filtered in JavaScript - only named reviews come through
                    if not reviews:
                        print(f"   ⚠️  Skipped: No named reviews found")
                        print()
                        continue
                    
                    added_count = 0
                    duplicate_count = 0
                    
                    for review in reviews:
                        # Check for duplicates before adding
                        if self.is_duplicate_review(
                            company_data.get('companyName', ''),
                            review.get('reviewerName', ''),
                            review.get('reviewText', '')
                        ):
                            duplicate_count += 1
                            continue
                        
                        # FIXED: Proper column mapping to match headers exactly
                        row = {
                            'Company': company_data.get('companyName', ''),
                            'Service Provider': company_data.get('companyName', ''),
                            'Service': review.get('service', '') or (', '.join(company_data.get('services', [])[:3]) if company_data.get('services') else ''),
                            'Project Summary': review.get('projectSummary', ''),
                            'Start Date': review.get('startDate', ''),
                            'Budget': review.get('budget', ''),
                            'Rating': review.get('rating', ''),
                            'Review': review.get('reviewText', ''),
                            'Reviewer Name': review.get('reviewerName', ''),
                            'Reviewer Position': review.get('reviewerPosition', ''),
                            'Reviewer Company': review.get('reviewerCompany', ''),
                            'Company Outsourced Industry': review.get('reviewerIndustry', ''),
                            'Person LinkedIn URL': '',
                            'Company URL': company_data.get('companyUrl', ''),
                            'Reviewer Location': review.get('reviewerLocation', '') or company_data.get('location', ''),
                            'Employee Size': company_data.get('employeeSize', ''),
                            'Job Change': '',
                        }
                        self.data.append(row)
                        added_count += 1
                    
                    print(f"   ✅ Added {added_count} unique review(s)")
                    if duplicate_count > 0:
                        print(f"   🔄 Skipped {duplicate_count} duplicate(s)")
                
                # Human-like delay
                await asyncio.sleep(self.delay)
                print()
            
            await browser.close()
        
        elapsed = time.time() - start_time
        
        print("=" * 80)
        print(f"✅ SCRAPING COMPLETE!")
        print("=" * 80)
        print(f"  ⏱️  Time: {elapsed:.1f} seconds")
        print(f"  📊 Records: {len(self.data)}")
        print(f"  🏢 Companies: {len(set(r['Company'] for r in self.data))}")
        print(f"  ⭐ Reviews: {sum(1 for r in self.data if r['Review'])}")
        print(f"  👤 Unique reviewers: {len(set(r['Reviewer Name'] for r in self.data if r['Reviewer Name']))}")
        print("=" * 80)
        print()
    
    def export_to_excel(self, filename: str = 'GoodFirms_AI_Companies_USA_FIXED.xlsx'):
        """Export data to Excel with proper formatting"""
        if not self.data:
            print("❌ No data to export!")
            return
        
        # Define columns in exact order needed
        columns = [
            'Company',
            'Service Provider',
            'Service',
            'Project Summary',
            'Start Date',
            'Budget',
            'Rating',
            'Review',
            'Reviewer Name',
            'Reviewer Position',
            'Reviewer Company',
            'Company Outsourced Industry',
            'Person LinkedIn URL',
            'Company URL',
            'Reviewer Location',
            'Employee Size',
            'Job Change'
        ]
        
        # Create DataFrame with explicit column order
        df = pd.DataFrame(self.data, columns=columns)
        
        # Clean data
        df = df.fillna('')
        
        # Remove rows where all fields are empty
        df = df[df.astype(str).apply(lambda x: x.str.strip().str.len().sum(), axis=1) > 0]
        
        # Remove exact duplicate rows
        df = df.drop_duplicates()
        
        # Export
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Companies & Reviews')
            
            worksheet = writer.sheets['Companies & Reviews']
            
            # Set column widths - ALIGNED WITH ACTUAL COLUMNS
            column_widths = {
                'A': 25,  # Company
                'B': 25,  # Service Provider
                'C': 20,  # Service
                'D': 40,  # Project Summary
                'E': 15,  # Start Date
                'F': 15,  # Budget
                'G': 10,  # Rating
                'H': 60,  # Review
                'I': 25,  # Reviewer Name
                'J': 30,  # Reviewer Position
                'K': 30,  # Reviewer Company
                'L': 20,  # Company Outsourced Industry
                'M': 30,  # Person LinkedIn URL
                'N': 50,  # Company URL
                'O': 25,  # Reviewer Location
                'P': 15,  # Employee Size
                'Q': 15,  # Job Change
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
        
        print(f"✅ Excel file created: {filename}")
        print(f"   📊 Total rows: {len(df)}")
        print(f"   🏢 Unique companies: {df['Company'].nunique()}")
        print(f"   👤 All reviews have named reviewers: {(df['Reviewer Name'] != '').all()}")
        print(f"   💼 Reviews with position: {(df['Reviewer Position'] != '').sum()}")
        print(f"   🏢 Reviews with company: {(df['Reviewer Company'] != '').sum()}")
        print(f"   ⭐ Reviews with rating: {(df['Rating'] != '').sum()}")
        print(f"   💰 Reviews with budget: {(df['Budget'] != '').sum()}")
        print(f"   📍 Reviews with location: {(df['Reviewer Location'] != '').sum()}")


async def main():
    """Run the scraper"""
    
    # ============ CONFIGURATION ============
    BASE_URL = "https://www.goodfirms.co/artificial-intelligence/usa"
    MAX_COMPANIES = 15      # Number of companies to scrape
    HEADLESS = False        # Set True to hide browser
    # =======================================
    
    scraper = HumanLikeGoodFirmsScraper(BASE_URL)
    await scraper.scrape(max_companies=MAX_COMPANIES, headless=HEADLESS)
    scraper.export_to_excel()
    
    print("\n✅ ALL DONE! Check your Excel file.\n")


if __name__ == "__main__":
    asyncio.run(main())
