import json
import os
import sys
from datetime import datetime
from pathlib import Path
import importlib.util
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
import uuid

class BaseScraperInterface(ABC):
    """Abstract base class that all website scrapers must implement"""
    
    @abstractmethod
    def get_scraper_info(self) -> Dict[str, str]:
        """Return scraper metadata (name, version, supported_sites, etc.)"""
        pass
    
    @abstractmethod
    def scrape_announcements(self, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape basic announcements/articles list"""
        pass
    
    @abstractmethod
    def scrape_full_content(self, announcement_urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Scrape full content from announcement URLs"""
        pass
    
    @abstractmethod
    def validate_date_format(self, date_str: str) -> bool:
        """Validate if date format is supported by this scraper"""
        pass

class ScraperResult:
    """Standardized result container with deduplication support"""
    
    def __init__(self, scraper_name: str, website: str, existing_urls: Set[str] = None):
        self.scraper_name = scraper_name
        self.website = website
        self.scraped_at = datetime.now().isoformat()
        self.session_id = str(uuid.uuid4())
        self.announcements = []
        self.full_content = []
        self.metadata = {}
        self.errors = []
        self.statistics = {}
        self.existing_urls = existing_urls or set()
        self.new_urls = set()
        self.skipped_duplicates = 0
    
    def add_announcement(self, announcement: Dict[str, Any]):
        """Add announcement if URL is not a duplicate"""
        url = announcement.get('url', '')
        
        if url and url in self.existing_urls:
            self.skipped_duplicates += 1
            return False  # Skip duplicate
        
        standardized = self._standardize_announcement(announcement)
        self.announcements.append(standardized)
        
        if url:
            self.new_urls.add(url)
        
        return True  # Added new item
    
    def add_full_content(self, content: Dict[str, Any]):
        """Add full content"""
        standardized = self._standardize_content(content)
        self.full_content.append(standardized)
    
    def _standardize_announcement(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize announcement format"""
        return {
            'id': announcement.get('id', str(uuid.uuid4())),
            'title': announcement.get('title', ''),
            'url': announcement.get('url', ''),
            'date': announcement.get('date', ''),
            'category': announcement.get('category', 'General'),
            'excerpt': announcement.get('excerpt', ''),
            'source_website': self.website,
            'scraped_at': self.scraped_at,
            'raw_data': announcement  # Preserve original data
        }
    
    def _standardize_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize full content format"""
        return {
            'id': content.get('id', str(uuid.uuid4())),
            'url': content.get('url', ''),
            'title': content.get('title', ''),
            'date_published': content.get('date_published', ''),
            'full_content': content.get('full_content', ''),
            'word_count': content.get('word_count', 0),
            'images': content.get('images', []),
            'links': content.get('links', []),
            'contact_info': content.get('contact_info', ''),
            'tags': content.get('tags', []),
            'comments': content.get('comments', []),
            'metadata': content.get('metadata', {}),
            'source_website': self.website,
            'scraped_at': self.scraped_at,
            'raw_data': content  # Preserve original data
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'scraper_info': {
                'scraper_name': self.scraper_name,
                'website': self.website,
                'scraped_at': self.scraped_at,
                'session_id': self.session_id
            },
            'statistics': {
                'total_announcements': len(self.announcements),
                'total_full_content': len(self.full_content),
                'total_errors': len(self.errors),
                'skipped_duplicates': self.skipped_duplicates,
                'new_urls_found': len(self.new_urls),
                **self.statistics
            },
            'announcements': self.announcements,
            'full_content': self.full_content,
            'metadata': self.metadata,
            'errors': self.errors
        }

class FeedGenerator:
    """Generate lightweight JSON feeds for web display"""
    
    def __init__(self, feeds_directory: str = "feeds"):
        self.feeds_directory = Path(feeds_directory)
        self.feeds_directory.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.latest_by_scraper_dir = self.feeds_directory / "latest_by_scraper"
        self.latest_by_scraper_dir.mkdir(exist_ok=True)
        
        self.archive_dir = self.feeds_directory / "archive"
        self.archive_dir.mkdir(exist_ok=True)
    
    def create_lightweight_item(self, item: Dict[str, Any], item_type: str = 'announcement') -> Dict[str, Any]:
        """Extract only essential fields for web display"""
        
        if item_type == 'announcement':
            return {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'date': item.get('date', ''),
                'category': item.get('category', 'General'),
                'excerpt': item.get('excerpt', '')[:200] if item.get('excerpt') else '',  # Limit excerpt
                'source_website': item.get('source_website', ''),
                'scraped_at': item.get('scraped_at', '')
            }
        else:  # full_content
            return {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'date_published': item.get('date_published', ''),
                'source_website': item.get('source_website', ''),
                'scraped_at': item.get('scraped_at', ''),
                'word_count': item.get('word_count', 0)
            }
    
    def generate_latest_feed(self, master_data: Dict[str, Any], max_items: int = 100) -> str:
        """Generate latest feed across all scrapers"""
        
        all_items = []
        
        for scraper_name, scraper_data in master_data.get('results_by_scraper', {}).items():
            # Collect announcements
            for announcement in scraper_data.get('announcements', []):
                lightweight_item = self.create_lightweight_item(announcement, 'announcement')
                lightweight_item['scraper'] = scraper_name
                all_items.append(lightweight_item)
        
        # Sort by date (most recent first)
        all_items.sort(key=lambda x: x.get('date', '') or x.get('scraped_at', ''), reverse=True)
        
        # Limit to max_items
        latest_items = all_items[:max_items]
        
        feed = {
            'feed_type': 'latest',
            'generated_at': datetime.now().isoformat(),
            'total_items': len(latest_items),
            'max_items': max_items,
            'items': latest_items
        }
        
        # Save feed
        feed_path = self.feeds_directory / "latest_feed.json"
        with open(feed_path, 'w', encoding='utf-8') as f:
            json.dump(feed, f, indent=2, ensure_ascii=False)
        
        print(f"Latest feed generated: {feed_path} ({len(latest_items)} items)")
        return str(feed_path)
    
    def generate_scraper_feeds(self, master_data: Dict[str, Any], max_items_per_scraper: int = 50) -> List[str]:
        """Generate individual feeds for each scraper"""
        
        feed_paths = []
        
        for scraper_name, scraper_data in master_data.get('results_by_scraper', {}).items():
            items = []
            
            # Collect announcements
            for announcement in scraper_data.get('announcements', []):
                lightweight_item = self.create_lightweight_item(announcement, 'announcement')
                items.append(lightweight_item)
            
            # Sort by date (most recent first)
            items.sort(key=lambda x: x.get('date', '') or x.get('scraped_at', ''), reverse=True)
            
            # Limit to max_items
            latest_items = items[:max_items_per_scraper]
            
            feed = {
                'feed_type': 'scraper_specific',
                'scraper_name': scraper_name,
                'website': scraper_data.get('scraper_info', {}).get('website', 'Unknown'),
                'generated_at': datetime.now().isoformat(),
                'total_items': len(latest_items),
                'max_items': max_items_per_scraper,
                'items': latest_items
            }
            
            # Save feed
            feed_path = self.latest_by_scraper_dir / f"{scraper_name}.json"
            with open(feed_path, 'w', encoding='utf-8') as f:
                json.dump(feed, f, indent=2, ensure_ascii=False)
            
            feed_paths.append(str(feed_path))
            print(f"Scraper feed generated: {feed_path} ({len(latest_items)} items)")
        
        return feed_paths
    
    def generate_monthly_archive(self, master_data: Dict[str, Any], year: int, month: int) -> str:
        """Generate monthly archive feed"""
        
        month_str = f"{year}-{month:02d}"
        all_items = []
        
        for scraper_name, scraper_data in master_data.get('results_by_scraper', {}).items():
            # Collect items from specified month
            for announcement in scraper_data.get('announcements', []):
                date = announcement.get('date', '')
                if date.startswith(month_str):
                    lightweight_item = self.create_lightweight_item(announcement, 'announcement')
                    lightweight_item['scraper'] = scraper_name
                    all_items.append(lightweight_item)
        
        # Sort by date
        all_items.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        feed = {
            'feed_type': 'monthly_archive',
            'year': year,
            'month': month,
            'generated_at': datetime.now().isoformat(),
            'total_items': len(all_items),
            'items': all_items
        }
        
        # Save feed
        feed_path = self.archive_dir / f"{year}-{month:02d}.json"
        with open(feed_path, 'w', encoding='utf-8') as f:
            json.dump(feed, f, indent=2, ensure_ascii=False)
        
        print(f"Monthly archive generated: {feed_path} ({len(all_items)} items)")
        return str(feed_path)
    
    def generate_feed_index(self, master_data: Dict[str, Any]) -> str:
        """Generate index of all available feeds"""
        
        # Get list of available scraper feeds
        scraper_feeds = []
        if self.latest_by_scraper_dir.exists():
            scraper_feeds = [f.stem for f in self.latest_by_scraper_dir.glob("*.json")]
        
        # Get list of monthly archives
        monthly_archives = []
        if self.archive_dir.exists():
            monthly_archives = [f.stem for f in self.archive_dir.glob("*.json")]
        
        index = {
            'generated_at': datetime.now().isoformat(),
            'feeds': {
                'latest': 'latest_feed.json',
                'by_scraper': scraper_feeds,
                'monthly_archives': monthly_archives
            },
            'statistics': master_data.get('summary', {}),
            'available_scrapers': list(master_data.get('results_by_scraper', {}).keys())
        }
        
        # Save index
        index_path = self.feeds_directory / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"Feed index generated: {index_path}")
        return str(index_path)

class ScraperOrchestrator:
    """Main orchestrator with deduplication and feed generation support"""
    
    def __init__(self, scrapers_directory: str = "scrapers", 
                 output_directory: str = "scraped_data", 
                 master_file: str = "master_scraped_data.json",
                 feeds_directory: str = "feeds"):
        self.scrapers_directory = Path(scrapers_directory)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        self.master_file_path = self.output_directory / master_file
        
        self.feed_generator = FeedGenerator(feeds_directory)
        
        self.loaded_scrapers = {}
        self.results = {}
    
    def load_existing_data(self) -> Dict[str, Any]:
        """Load existing data from master file"""
        if not self.master_file_path.exists():
            return {
                'scraping_history': {
                    'first_scrape': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_scrapes': 0
                },
                'summary': {
                    'total_announcements': 0,
                    'total_full_content': 0,
                    'total_errors': 0
                },
                'results_by_scraper': {}
            }
        
        try:
            with open(self.master_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
            return self.load_existing_data()  # Return empty structure
    
    def get_existing_urls(self, scraper_name: str = None) -> Set[str]:
        """Get set of existing URLs from master file"""
        existing_data = self.load_existing_data()
        existing_urls = set()
        
        scrapers_to_check = [scraper_name] if scraper_name else existing_data.get('results_by_scraper', {}).keys()
        
        for scraper in scrapers_to_check:
            scraper_data = existing_data.get('results_by_scraper', {}).get(scraper, {})
            
            # Get URLs from announcements
            for announcement in scraper_data.get('announcements', []):
                url = announcement.get('url')
                if url:
                    existing_urls.add(url)
            
            # Get URLs from full content
            for content in scraper_data.get('full_content', []):
                url = content.get('url')
                if url:
                    existing_urls.add(url)
        
        return existing_urls
    
    def discover_scrapers(self) -> Dict[str, BaseScraperInterface]:
        """Dynamically discover and load scraper modules"""
        scrapers = {}
        
        if not self.scrapers_directory.exists():
            print(f"Scrapers directory not found: {self.scrapers_directory}")
            return scrapers
        
        # Add the scrapers directory to Python path temporarily
        scrapers_path_str = str(self.scrapers_directory.absolute())
        if scrapers_path_str not in sys.path:
            sys.path.insert(0, scrapers_path_str)
        
        scraper_files = list(self.scrapers_directory.glob("*_scraper.py"))
        print(f"Found {len(scraper_files)} potential scraper files")
        
        for scraper_file in scraper_files:
            try:
                scraper_name = scraper_file.stem
                spec = importlib.util.spec_from_file_location(scraper_name, scraper_file)
                if spec is None:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                if module is None:
                    continue
                
                sys.modules[scraper_name] = module
                spec.loader.exec_module(module)
                
                # Look for scraper classes
                for attr_name in dir(module):
                    if attr_name.startswith('_') or attr_name == 'BaseScraperInterface':
                        continue
                        
                    attr = getattr(module, attr_name)
                    
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and
                        attr != BaseScraperInterface):
                        
                        # Check if it inherits from BaseScraperInterface
                        for base in attr.__mro__:
                            if base.__name__ == 'BaseScraperInterface':
                                try:
                                    scraper_instance = attr()
                                    if hasattr(scraper_instance, 'get_scraper_info'):
                                        scrapers[scraper_name] = scraper_instance
                                        print(f"Loaded scraper: {scraper_name}")
                                except Exception as e:
                                    print(f"Error instantiating {attr_name}: {e}")
                                break
                        
            except Exception as e:
                print(f"Error loading scraper {scraper_file}: {e}")
        
        # Clean up sys.path
        if scrapers_path_str in sys.path:
            sys.path.remove(scrapers_path_str)
        
        self.loaded_scrapers = scrapers
        return scrapers
    
    def run_scraper(self, scraper_name: str, start_date: str, end_date: str, 
                   scrape_full_content: bool = True, **kwargs) -> ScraperResult:
        """Run a specific scraper with deduplication"""
        
        if scraper_name not in self.loaded_scrapers:
            available = list(self.loaded_scrapers.keys())
            raise ValueError(f"Scraper '{scraper_name}' not found. Available: {available}")
        
        scraper = self.loaded_scrapers[scraper_name]
        scraper_info = scraper.get_scraper_info()
        
        print(f"Running scraper: {scraper_info['name']} for {scraper_info.get('website', 'Unknown')}")
        
        # Get existing URLs for this scraper
        existing_urls = self.get_existing_urls(scraper_name)
        print(f"Found {len(existing_urls)} existing URLs, checking for duplicates...")
        
        # Create result container with existing URLs
        result = ScraperResult(
            scraper_info['name'], 
            scraper_info.get('website', 'Unknown'),
            existing_urls
        )
        
        try:
            # Step 1: Scrape announcements
            print("Step 1: Scraping announcements list...")
            announcements = scraper.scrape_announcements(start_date, end_date, **kwargs)
            
            new_announcements = []
            for announcement in announcements:
                if result.add_announcement(announcement):
                    new_announcements.append(announcement)
            
            print(f"Found {len(announcements)} total announcements")
            print(f"Added {len(new_announcements)} new announcements")
            print(f"Skipped {result.skipped_duplicates} duplicates")
            
            # Step 2: Scrape full content for new URLs only
            if scrape_full_content and new_announcements:
                print("Step 2: Scraping full content for new items only...")
                new_urls = [ann.get('url', '') for ann in new_announcements if ann.get('url')]
                
                if new_urls:
                    full_content_data = scraper.scrape_full_content(new_urls, **kwargs)
                    
                    for content in full_content_data:
                        result.add_full_content(content)
                    
                    print(f"Scraped full content for {len(full_content_data)} new items")
            
            # Update statistics
            result.statistics.update({
                'date_range': f"{start_date} to {end_date}",
                'success_rate': len(result.full_content) / len(result.announcements) if result.announcements else 0
            })
            
        except Exception as e:
            error_msg = f"Error running scraper {scraper_name}: {e}"
            result.errors.append(error_msg)
            print(error_msg)
        
        # Store result
        self.results[scraper_name] = result
        return result
    
    def run_all_scrapers(self, start_date: str, end_date: str, 
                        scrape_full_content: bool = True, **kwargs) -> Dict[str, ScraperResult]:
        """Run all available scrapers with deduplication"""
        results = {}
        
        for scraper_name in self.loaded_scrapers:
            try:
                result = self.run_scraper(scraper_name, start_date, end_date, 
                                        scrape_full_content, **kwargs)
                results[scraper_name] = result
            except Exception as e:
                print(f"Failed to run scraper {scraper_name}: {e}")
        
        return results
    
    def update_master_file(self, new_results: Dict[str, ScraperResult]) -> str:
        """Update the master JSON file with new results"""
        
        # Load existing data
        existing_data = self.load_existing_data()
        
        # Update metadata
        existing_data['scraping_history']['last_updated'] = datetime.now().isoformat()
        existing_data['scraping_history']['total_scrapes'] = existing_data['scraping_history'].get('total_scrapes', 0) + 1
        
        # Update each scraper's data
        for scraper_name, result in new_results.items():
            if scraper_name not in existing_data['results_by_scraper']:
                # New scraper - add all data
                existing_data['results_by_scraper'][scraper_name] = result.to_dict()
            else:
                # Existing scraper - append new data
                existing_scraper_data = existing_data['results_by_scraper'][scraper_name]
                new_scraper_data = result.to_dict()
                
                # Update scraper info (in case version changed)
                existing_scraper_data['scraper_info'].update(new_scraper_data['scraper_info'])
                
                # Append new announcements
                existing_scraper_data['announcements'].extend(new_scraper_data['announcements'])
                
                # Append new full content
                existing_scraper_data['full_content'].extend(new_scraper_data['full_content'])
                
                # Append errors
                existing_scraper_data['errors'].extend(new_scraper_data['errors'])
                
                # Update statistics
                old_stats = existing_scraper_data['statistics']
                new_stats = new_scraper_data['statistics']
                
                existing_scraper_data['statistics'] = {
                    'total_announcements': len(existing_scraper_data['announcements']),
                    'total_full_content': len(existing_scraper_data['full_content']),
                    'total_errors': len(existing_scraper_data['errors']),
                    'last_scrape_new_items': new_stats.get('total_announcements', 0),
                    'last_scrape_skipped': new_stats.get('skipped_duplicates', 0),
                    'last_scrape_date': new_scraper_data['scraper_info']['scraped_at']
                }
        
        # Update summary
        total_announcements = sum(
            len(data['announcements']) 
            for data in existing_data['results_by_scraper'].values()
        )
        total_full_content = sum(
            len(data['full_content']) 
            for data in existing_data['results_by_scraper'].values()
        )
        total_errors = sum(
            len(data['errors']) 
            for data in existing_data['results_by_scraper'].values()
        )
        
        existing_data['summary'] = {
            'total_announcements': total_announcements,
            'total_full_content': total_full_content,
            'total_errors': total_errors,
            'scrapers_count': len(existing_data['results_by_scraper']),
            'last_updated': datetime.now().isoformat()
        }
        
        # Save updated data
        with open(self.master_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"Master file updated: {self.master_file_path}")
        return str(self.master_file_path)
    
    def generate_feeds(self, max_latest_items: int = 100, max_per_scraper: int = 50):
        """Generate all feed files"""
        print("\n=== Generating Feeds ===")
        
        # Load master data
        master_data = self.load_existing_data()
        
        # Generate latest feed
        self.feed_generator.generate_latest_feed(master_data, max_latest_items)
        
        # Generate scraper-specific feeds
        self.feed_generator.generate_scraper_feeds(master_data, max_per_scraper)
        
        # Generate feed index
        self.feed_generator.generate_feed_index(master_data)
        
        print("=== Feed Generation Complete ===\n")
    
    def generate_report(self, results: Dict[str, ScraperResult]) -> str:
        """Generate a summary report including deduplication stats"""
        existing_data = self.load_existing_data()
        
        report_lines = [
            "WEB SCRAPING REPORT",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Master file: {self.master_file_path}",
            ""
        ]
        
        # Current run stats
        new_announcements = 0
        new_content = 0
        skipped_duplicates = 0
        
        for scraper_name, result in results.items():
            report_lines.extend([
                f"Scraper: {scraper_name}",
                f"  Website: {result.website}",
                f"  New Announcements: {len(result.announcements)}",
                f"  New Full Content: {len(result.full_content)}",
                f"  Skipped Duplicates: {result.skipped_duplicates}",
                f"  Errors: {len(result.errors)}",
                ""
            ])
            
            new_announcements += len(result.announcements)
            new_content += len(result.full_content)
            skipped_duplicates += result.skipped_duplicates
        
        # Overall stats from master file
        summary = existing_data.get('summary', {})
        history = existing_data.get('scraping_history', {})
        
        report_lines.extend([
            "CURRENT RUN SUMMARY",
            f"New Announcements: {new_announcements}",
            f"New Full Content: {new_content}",
            f"Skipped Duplicates: {skipped_duplicates}",
            "",
            "MASTER FILE SUMMARY",
            f"Total Scrapers: {summary.get('scrapers_count', 0)}",
            f"Total Announcements: {summary.get('total_announcements', 0)}",
            f"Total Full Content: {summary.get('total_full_content', 0)}",
            f"Total Errors: {summary.get('total_errors', 0)}",
            f"First Scrape: {history.get('first_scrape', 'Unknown')}",
            f"Total Scraping Sessions: {history.get('total_scrapes', 0)}",
        ])
        
        return "\n".join(report_lines)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Web Scraper Orchestrator with Rolling Feeds')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--scraper', help='Run specific scraper (default: run all)')
    parser.add_argument('--scrapers-dir', default='scrapers', help='Directory containing scraper modules')
    parser.add_argument('--output-dir', default='scraped_data', help='Output directory')
    parser.add_argument('--feeds-dir', default='feeds', help='Feeds output directory')
    parser.add_argument('--master-file', default='master_scraped_data.json', help='Master file name')
    parser.add_argument('--no-full-content', action='store_true', help='Skip full content scraping')
    parser.add_argument('--report-only', action='store_true', help='Generate report only')
    parser.add_argument('--max-latest', type=int, default=100, help='Max items in latest feed')
    parser.add_argument('--max-per-scraper', type=int, default=50, help='Max items per scraper feed')
    parser.add_argument('--feeds-only', action='store_true', help='Only regenerate feeds from existing data')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = ScraperOrchestrator(args.scrapers_dir, args.output_dir, args.master_file, args.feeds_dir)
    
    # If feeds-only mode, skip scraping
    if args.feeds_only:
        print("Feeds-only mode: Regenerating feeds from existing data...")
        orchestrator.generate_feeds(args.max_latest, args.max_per_scraper)
        print("Feeds regenerated successfully!")
        sys.exit(0)
    
    # Discover scrapers
    scrapers = orchestrator.discover_scrapers()
    
    if not scrapers:
        print("No scrapers found! Please check your scrapers directory.")
        sys.exit(1)
    
    print(f"Discovered {len(scrapers)} scrapers: {list(scrapers.keys())}")
    
    # Run scrapers
    scrape_full_content = not args.no_full_content
    
    if args.scraper:
        # Run specific scraper
        if args.scraper not in scrapers:
            print(f"Scraper '{args.scraper}' not found")
            sys.exit(1)
        results = {args.scraper: orchestrator.run_scraper(args.scraper, args.start_date, args.end_date, scrape_full_content)}
    else:
        # Run all scrapers
        results = orchestrator.run_all_scrapers(args.start_date, args.end_date, scrape_full_content)
    
    # Update master file
    if not args.report_only:
        master_file = orchestrator.update_master_file(results)
        print(f"Data saved to master file: {master_file}")
        
        # Generate feeds after updating master file
        orchestrator.generate_feeds(args.max_latest, args.max_per_scraper)
    
    # Generate and print report
    report = orchestrator.generate_report(results)
    print("\n" + report)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = orchestrator.output_directory / f"report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_file}")

if __name__ == "__main__":
    main()


# USAGE EXAMPLES:
# 
# 1. Run all scrapers and generate feeds:
#    python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30
#
# 2. Run specific scraper:
#    python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --scraper fda_scraper
#
# 3. Regenerate feeds only (no scraping):
#    python base_scraper.py --feeds-only
#
# 4. Custom feed sizes:
#    python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --max-latest 200 --max-per-scraper 100
#
# 5. Custom output directories:
#    python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --feeds-dir public/feeds
