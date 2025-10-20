# Web Scraper Orchestrator

A flexible, extensible web scraping framework that orchestrates multiple website scrapers with built-in deduplication, data standardization, and comprehensive content extraction.

## What This Does

This project provides a robust orchestration layer for managing multiple web scrapers. Think of it as a command center that:
- Discovers and loads scraper modules dynamically
- Runs scrapers individually or all at once
- Prevents duplicate data collection
- Standardizes output across different websites
- Maintains a master database of all scraped content
- Generates detailed reports

Currently includes scrapers for:
- **FDA Press Announcements** - Drug safety, food recalls, medical devices
- **NIH News Releases** - Medical research, clinical trials, health breakthroughs

## Features

### Core Capabilities
- **Plugin Architecture**: Drop scraper files into the `scrapers/` directory and they're automatically discovered
- **Smart Deduplication**: Tracks URLs across scraping sessions to avoid redundant data collection
- **Two-Phase Scraping**: First gets announcement lists, then optionally fetches full content
- **Standardized Output**: All scrapers follow the same data structure
- **Master Database**: Cumulative JSON file tracks all historical data
- **Date Range Filtering**: Scrape only content within specific timeframes
- **Detailed Reporting**: Session summaries and cumulative statistics

### Data Extraction
Each scraper captures:
- Basic announcements (title, URL, date, category, excerpt)
- Full content (complete text, word count, images, links)
- Contact information
- Metadata and tags
- Related resources

## Installation

### Requirements
```bash
Python 3.7+
```

### Dependencies
```bash
pip install requests beautifulsoup4
```

That's it. No heavy frameworks, just the essentials.

## Quick Start

### Basic Usage

Run all scrapers for a specific date range:
```bash
python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30
```

Run a specific scraper:
```bash
python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --scraper fda_scraper
```

Skip full content extraction (faster, announcements only):
```bash
python base_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --no-full-content
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--start-date` | Start date (YYYY-MM-DD) | Required |
| `--end-date` | End date (YYYY-MM-DD) | Required |
| `--scraper` | Run specific scraper only | All scrapers |
| `--scrapers-dir` | Directory with scraper modules | `scrapers` |
| `--output-dir` | Where to save results | `scraped_data` |
| `--master-file` | Master database filename | `master_scraped_data.json` |
| `--no-full-content` | Skip full content scraping | False |
| `--report-only` | Generate report without saving | False |

## Project Structure

```
web-scraper-orchestrator/
├── base_scraper.py              # Main orchestrator
├── scrapers/                     # Scraper modules directory
│   ├── fda_scraper.py           # FDA press announcements
│   └── nih_scraper.py           # NIH news releases
├── scraped_data/                 # Output directory (auto-created)
│   ├── master_scraped_data.json # Cumulative database
│   └── report_*.txt             # Session reports
└── README.md
```

## How It Works

### The Orchestration Flow

1. **Discovery Phase**: Scans `scrapers/` directory for `*_scraper.py` files
2. **Loading Phase**: Dynamically imports and instantiates scraper classes
3. **Deduplication Check**: Loads existing URLs from master file
4. **Scraping Phase**: 
   - Fetches announcement lists within date range
   - Filters out duplicate URLs
   - Optionally scrapes full content for new items only
5. **Data Merge**: Updates master file with new data
6. **Reporting**: Generates statistics and saves session report

### Deduplication Magic

The orchestrator maintains a set of all previously scraped URLs. When running again:
- Compares new URLs against existing ones
- Only fetches full content for genuinely new items
- Reports how many duplicates were skipped
- Saves bandwidth and time

Example output:
```
Found 45 total announcements
Added 12 new announcements
Skipped 33 duplicates
```

## Creating Custom Scrapers

Want to add a new website? Create a new scraper that implements the `BaseScraperInterface`.

### Scraper Template

```python
from base_scraper import BaseScraperInterface
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any

class YourWebsiteScraper(BaseScraperInterface):
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://example.com"
    
    def get_scraper_info(self) -> Dict[str, str]:
        """Return scraper metadata"""
        return {
            'name': 'Your Website Scraper',
            'version': '1.0',
            'website': 'example.com',
            'description': 'Scrapes announcements from example.com',
            'supported_date_format': 'YYYY-MM-DD'
        }
    
    def validate_date_format(self, date_str: str) -> bool:
        """Validate date format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def scrape_announcements(self, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape announcement list"""
        announcements = []
        
        # Your scraping logic here
        # Return list of announcements with:
        # - id, title, url, date, category, excerpt
        
        return announcements
    
    def scrape_full_content(self, announcement_urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Scrape full content from URLs"""
        full_content = []
        
        # Your content extraction logic here
        # Return list with:
        # - id, url, title, date_published, full_content, word_count, etc.
        
        return full_content
```

### Required Fields

**Announcements** must include:
- `id`: Unique identifier (UUID recommended)
- `title`: Announcement headline
- `url`: Full URL to the announcement
- `date`: Publication date (YYYY-MM-DD)
- `category`: Content category
- `excerpt`: Brief summary

**Full Content** must include:
- `id`: Unique identifier
- `url`: Source URL
- `title`: Article title
- `full_content`: Complete text content
- `word_count`: Number of words
- `date_published`: Publication date

### Save Your Scraper

1. Name it with `_scraper.py` suffix (e.g., `cdc_scraper.py`)
2. Place it in the `scrapers/` directory
3. That's it - the orchestrator will find it automatically

## Output Format

### Master Database Structure

```json
{
  "scraping_history": {
    "first_scrape": "2024-09-15T10:30:00",
    "last_updated": "2024-10-15T14:22:00",
    "total_scrapes": 15
  },
  "summary": {
    "total_announcements": 342,
    "total_full_content": 298,
    "total_errors": 5,
    "scrapers_count": 2
  },
  "results_by_scraper": {
    "fda_scraper": {
      "scraper_info": { ... },
      "statistics": { ... },
      "announcements": [ ... ],
      "full_content": [ ... ],
      "errors": [ ... ]
    }
  }
}
```

### Session Report Example

```
WEB SCRAPING REPORT
Generated at: 2024-10-15 14:22:35
Master file: scraped_data/master_scraped_data.json

Scraper: fda_scraper
  Website: fda.gov
  New Announcements: 12
  New Full Content: 12
  Skipped Duplicates: 33
  Errors: 0

CURRENT RUN SUMMARY
New Announcements: 12
New Full Content: 12
Skipped Duplicates: 33

MASTER FILE SUMMARY
Total Scrapers: 2
Total Announcements: 342
Total Full Content: 298
Total Errors: 5
First Scrape: 2024-09-15T10:30:00
Total Scraping Sessions: 15
```

## Included Scrapers

### FDA Scraper (`fda_scraper.py`)

Scrapes FDA press announcements including:
- Drug safety communications
- Food recalls and safety alerts
- Medical device updates
- Tobacco product announcements

**Categories**: Drug Safety, Food Safety, Medical Device, Tobacco Products, General

**Standalone usage**:
```bash
python scrapers/fda_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --full-content
```

### NIH Scraper (`nih_scraper.py`)

Scrapes NIH news releases covering:
- Research findings and breakthroughs
- Clinical trial announcements
- Health policy updates
- Grant and funding news

**Categories**: Research, Cancer, Neuroscience, Cardiovascular, Vaccines, Genomics, and more

**Standalone usage**:
```bash
python scrapers/nih_scraper.py --start-date 2024-09-01 --end-date 2024-09-30 --full-content
```

## Advanced Usage

### Programmatic Usage

```python
from base_scraper import ScraperOrchestrator

# Initialize orchestrator
orchestrator = ScraperOrchestrator(
    scrapers_directory="scrapers",
    output_directory="scraped_data",
    master_file="master_scraped_data.json"
)

# Discover scrapers
scrapers = orchestrator.discover_scrapers()
print(f"Found {len(scrapers)} scrapers")

# Run specific scraper
result = orchestrator.run_scraper(
    'fda_scraper',
    start_date='2024-09-01',
    end_date='2024-09-30',
    scrape_full_content=True
)

# Check what was found
print(f"New items: {len(result.announcements)}")
print(f"Duplicates skipped: {result.skipped_duplicates}")

# Update master file
orchestrator.update_master_file({'fda_scraper': result})

# Generate report
report = orchestrator.generate_report({'fda_scraper': result})
print(report)
```

### Custom Scraper Parameters

Pass custom parameters to scrapers via kwargs:
```python
result = orchestrator.run_scraper(
    'fda_scraper',
    start_date='2024-09-01',
    end_date='2024-09-30',
    max_pages=20,      # Custom parameter
    delay=2.0          # Custom parameter
)
```

## Performance Tips

1. **Start Small**: Test with short date ranges first
2. **Use --no-full-content**: For quick announcement checks
3. **Adjust Delays**: Increase delay between requests if getting rate limited
4. **Run Specific Scrapers**: Use `--scraper` for faster targeted scraping
5. **Monitor Duplicates**: High duplicate counts mean you can reduce scraping frequency

## Error Handling

The orchestrator is resilient:
- Individual scraper failures don't stop other scrapers
- Network errors are logged but don't crash the process
- Partial results are always saved
- Error details are captured in the output

## Limitations

- **JavaScript-Heavy Sites**: These scrapers work with static HTML. Sites requiring JavaScript execution aren't supported out of the box
- **Authentication**: No built-in support for login-required content
- **Rate Limiting**: Basic delay-based throttling only
- **Dynamic Dates**: Some pages may not have easily parseable dates

## Troubleshooting

**"No scrapers found"**
- Check that scraper files end with `_scraper.py`
- Verify scrapers directory path is correct
- Make sure scraper classes inherit from `BaseScraperInterface`

**"No content extracted"**
- Website structure may have changed
- Check network connectivity
- Verify the date range includes actual content
- Run with verbose logging to see what's happening

**High duplicate counts**
- Normal if scraping overlapping date ranges
- Indicates efficient deduplication is working
- Consider adjusting your scraping schedule

## Contributing

To add a new scraper:
1. Copy one of the existing scrapers as a template
2. Implement all required methods from `BaseScraperInterface`
3. Test standalone before adding to orchestrator
4. Submit a PR with your new scraper

## License

This project is open source. Use it, modify it, extend it.

## Future Enhancements

Potential additions:
- Async/concurrent scraping for better performance
- Database backend instead of JSON
- Web UI for monitoring and configuration
- Scheduled/cron job support
- Export to CSV/Excel
- Email notifications on completion
- Proxy rotation support
- Browser automation for JS-heavy sites

## Questions?

Check the code comments - they're extensive. Both the orchestrator and individual scrapers are well-documented internally.

---

**Happy Scraping!** 🕷️
