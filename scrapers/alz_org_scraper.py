#!/usr/bin/env python3
"""
Alzheimer's Association News Scraper
Scrapes news and press releases from alz.org
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
import uuid
import time
import re
import sys
from pathlib import Path

# Import base scraper if running standalone
try:
    from base_scraper import BaseScraperInterface
except ImportError:
    # If running standalone, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base_scraper import BaseScraperInterface


class AlzOrgScraper(BaseScraperInterface):
    """Scraper for Alzheimer's Association news from alz.org"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url = "https://www.alz.org"
        self.news_url = "https://www.alz.org/news"
        self.delay = 1.0  # Delay between requests in seconds
    
    def get_scraper_info(self) -> Dict[str, str]:
        """Return scraper metadata"""
        return {
            'name': 'Alzheimer\'s Association News Scraper',
            'version': '1.0',
            'website': 'alz.org',
            'description': 'Scrapes news and press releases from the Alzheimer\'s Association',
            'supported_date_format': 'YYYY-MM-DD'
        }
    
    def validate_date_format(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def scrape_announcements(self, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape basic announcements/articles list from alz.org/news
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional parameters
        
        Returns:
            List of announcement dictionaries
        """
        print(f"[ALZ.ORG] Scraping announcements from {start_date} to {end_date}...")
        
        # Validate dates
        if not self.validate_date_format(start_date) or not self.validate_date_format(end_date):
            print("Invalid date format. Use YYYY-MM-DD")
            return []
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        announcements = []
        
        # Try to scrape from the main news page
        try:
            response = self.session.get(self.news_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for news articles on the page
            # The structure appears to have news items as links with specific patterns
            # Based on the search results, news URLs follow pattern: /news/YYYY/article-slug
            
            # Find all links that match the news pattern
            news_links = soup.find_all('a', href=re.compile(r'/news/\d{4}/'))
            
            print(f"[ALZ.ORG] Found {len(news_links)} potential news articles")
            
            for link in news_links:
                try:
                    url = link.get('href', '')
                    
                    # Make absolute URL
                    if url.startswith('/'):
                        url = self.base_url + url
                    
                    # Extract year from URL to filter by date
                    year_match = re.search(r'/news/(\d{4})/', url)
                    if not year_match:
                        continue
                    
                    article_year = int(year_match.group(1))
                    
                    # Basic date filtering by year
                    if article_year < start_dt.year or article_year > end_dt.year:
                        continue
                    
                    # Get title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        # Try to find title in parent elements
                        parent = link.find_parent(['div', 'article', 'section'])
                        if parent:
                            title_elem = parent.find(['h2', 'h3', 'h4', 'h1'])
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # Try to get excerpt
                    excerpt = ""
                    parent = link.find_parent(['div', 'article', 'section'])
                    if parent:
                        # Look for description or excerpt text
                        desc = parent.find(['p', 'span', 'div'], class_=re.compile(r'(excerpt|description|summary)', re.I))
                        if desc:
                            excerpt = desc.get_text(strip=True)[:500]
                    
                    # Try to determine category
                    category = "Press Release"  # Default category
                    if parent:
                        cat_elem = parent.find(text=re.compile(r'(Press|Statement|Research|Blog)', re.I))
                        if cat_elem:
                            category = cat_elem.strip()
                    
                    # Create announcement entry
                    announcement = {
                        'id': str(uuid.uuid4()),
                        'title': title,
                        'url': url,
                        'date': f"{article_year}-01-01",  # Will be refined when we fetch full content
                        'category': category,
                        'excerpt': excerpt if excerpt else f"News article from {article_year}"
                    }
                    
                    announcements.append(announcement)
                    
                except Exception as e:
                    print(f"[ALZ.ORG] Error processing article link: {e}")
                    continue
            
            # Also try to search through the /news page for more specific listings
            # Look for common patterns in news listings
            article_containers = soup.find_all(['article', 'div'], class_=re.compile(r'(news|press|article|item)', re.I))
            
            for container in article_containers:
                try:
                    link_elem = container.find('a', href=re.compile(r'/news/\d{4}/'))
                    if not link_elem:
                        continue
                    
                    url = link_elem.get('href', '')
                    if url.startswith('/'):
                        url = self.base_url + url
                    
                    # Skip if already added
                    if any(a['url'] == url for a in announcements):
                        continue
                    
                    # Extract year
                    year_match = re.search(r'/news/(\d{4})/', url)
                    if not year_match:
                        continue
                    
                    article_year = int(year_match.group(1))
                    if article_year < start_dt.year or article_year > end_dt.year:
                        continue
                    
                    # Get title
                    title = link_elem.get_text(strip=True)
                    if not title:
                        title_elem = container.find(['h1', 'h2', 'h3', 'h4'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # Get excerpt
                    excerpt = ""
                    desc_elem = container.find(['p', 'div'], class_=re.compile(r'(excerpt|description|summary)', re.I))
                    if desc_elem:
                        excerpt = desc_elem.get_text(strip=True)[:500]
                    
                    announcement = {
                        'id': str(uuid.uuid4()),
                        'title': title,
                        'url': url,
                        'date': f"{article_year}-01-01",
                        'category': "Press Release",
                        'excerpt': excerpt if excerpt else f"News article from {article_year}"
                    }
                    
                    announcements.append(announcement)
                    
                except Exception as e:
                    print(f"[ALZ.ORG] Error processing article container: {e}")
                    continue
            
        except Exception as e:
            print(f"[ALZ.ORG] Error fetching news page: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_announcements = []
        for ann in announcements:
            if ann['url'] not in seen_urls:
                seen_urls.add(ann['url'])
                unique_announcements.append(ann)
        
        print(f"[ALZ.ORG] Found {len(unique_announcements)} unique announcements")
        return unique_announcements
    
    def scrape_full_content(self, announcement_urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape full content from announcement URLs
        
        Args:
            announcement_urls: List of URLs to scrape
            **kwargs: Additional parameters
        
        Returns:
            List of full content dictionaries
        """
        print(f"[ALZ.ORG] Scraping full content for {len(announcement_urls)} articles...")
        
        full_content_list = []
        
        for i, url in enumerate(announcement_urls, 1):
            try:
                print(f"[ALZ.ORG] Fetching {i}/{len(announcement_urls)}: {url}")
                
                # Add delay to be respectful
                if i > 1:
                    time.sleep(self.delay)
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title
                title = ""
                title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'(title|headline)', re.I))
                if not title_elem:
                    title_elem = soup.find('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                # Extract date
                date_published = ""
                # Look for date patterns
                date_elem = soup.find(['time', 'span', 'p'], class_=re.compile(r'(date|published|time)', re.I))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Try to parse various date formats
                    date_published = self._parse_date(date_text)
                
                # If no date found, try to extract from URL
                if not date_published:
                    year_match = re.search(r'/news/(\d{4})/', url)
                    if year_match:
                        date_published = f"{year_match.group(1)}-01-01"
                
                # Extract main content
                content = ""
                
                # Look for main content area
                content_elem = soup.find(['article', 'div'], class_=re.compile(r'(content|body|article|text|main)', re.I))
                if not content_elem:
                    content_elem = soup.find('article')
                if not content_elem:
                    # Try to find the largest text block
                    content_elem = soup.find('main')
                
                if content_elem:
                    # Extract all paragraphs
                    paragraphs = content_elem.find_all('p')
                    content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                # If no content found, try getting all paragraphs from body
                if not content or len(content) < 100:
                    all_paragraphs = soup.find_all('p')
                    content = '\n\n'.join([p.get_text(strip=True) for p in all_paragraphs if len(p.get_text(strip=True)) > 50])
                
                # Extract images
                images = []
                if content_elem:
                    img_tags = content_elem.find_all('img')
                    for img in img_tags:
                        img_src = img.get('src', '')
                        if img_src:
                            if img_src.startswith('/'):
                                img_src = self.base_url + img_src
                            images.append(img_src)
                
                # Extract links
                links = []
                if content_elem:
                    link_tags = content_elem.find_all('a', href=True)
                    for link in link_tags[:20]:  # Limit to first 20 links
                        link_url = link.get('href', '')
                        if link_url and not link_url.startswith('#'):
                            if link_url.startswith('/'):
                                link_url = self.base_url + link_url
                            links.append(link_url)
                
                # Calculate word count
                word_count = len(content.split()) if content else 0
                
                # Extract contact info if available
                contact_info = ""
                contact_elem = soup.find(['div', 'p'], class_=re.compile(r'contact', re.I))
                if contact_elem:
                    contact_info = contact_elem.get_text(strip=True)
                
                # Extract tags/categories
                tags = []
                tag_elems = soup.find_all(['span', 'a'], class_=re.compile(r'(tag|category|topic)', re.I))
                for tag in tag_elems[:10]:
                    tag_text = tag.get_text(strip=True)
                    if tag_text and len(tag_text) < 50:
                        tags.append(tag_text)
                
                # Create full content entry
                full_content = {
                    'id': str(uuid.uuid4()),
                    'url': url,
                    'title': title if title else "Untitled",
                    'date_published': date_published if date_published else "Unknown",
                    'full_content': content,
                    'word_count': word_count,
                    'images': images,
                    'links': links,
                    'contact_info': contact_info,
                    'tags': tags,
                    'metadata': {
                        'source': 'alz.org',
                        'scraper_version': '1.0'
                    }
                }
                
                full_content_list.append(full_content)
                print(f"[ALZ.ORG] Successfully scraped: {title[:60]}... ({word_count} words)")
                
            except Exception as e:
                print(f"[ALZ.ORG] Error scraping {url}: {e}")
                continue
        
        print(f"[ALZ.ORG] Successfully scraped {len(full_content_list)} articles")
        return full_content_list
    
    def _parse_date(self, date_str: str) -> str:
        """
        Parse various date formats and return YYYY-MM-DD format
        
        Args:
            date_str: Date string in various formats
        
        Returns:
            Date in YYYY-MM-DD format or empty string
        """
        date_str = date_str.strip()
        
        # Try various date formats
        formats = [
            '%B %d, %Y',  # January 1, 2025
            '%b %d, %Y',  # Jan 1, 2025
            '%Y-%m-%d',   # 2025-01-01
            '%m/%d/%Y',   # 01/01/2025
            '%d %B %Y',   # 1 January 2025
            '%B %Y',      # January 2025 (will use first of month)
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Try to extract year at least
        year_match = re.search(r'20\d{2}', date_str)
        if year_match:
            return f"{year_match.group(0)}-01-01"
        
        return ""


def main():
    """Standalone execution for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape news from alz.org')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--full-content', action='store_true', help='Scrape full content')
    parser.add_argument('--output', default='alz_org_output.json', help='Output file')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = AlzOrgScraper()
    
    # Get scraper info
    info = scraper.get_scraper_info()
    print(f"Starting {info['name']} v{info['version']}")
    print(f"Website: {info['website']}")
    
    # Scrape announcements
    announcements = scraper.scrape_announcements(args.start_date, args.end_date)
    print(f"\nFound {len(announcements)} announcements")
    
    # Scrape full content if requested
    full_content = []
    if args.full_content and announcements:
        urls = [ann['url'] for ann in announcements]
        full_content = scraper.scrape_full_content(urls)
    
    # Save results
    import json
    output = {
        'scraper_info': info,
        'scraped_at': datetime.now().isoformat(),
        'date_range': {
            'start': args.start_date,
            'end': args.end_date
        },
        'announcements': announcements,
        'full_content': full_content,
        'statistics': {
            'total_announcements': len(announcements),
            'total_full_content': len(full_content)
        }
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()