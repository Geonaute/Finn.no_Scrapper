# 🔍 Finn.no Deal Finder Pro

**The Ultimate Norwegian Marketplace Deal Hunter**

A powerful, beautiful web application to find the best deals on Finn.no - Norway's largest online marketplace with over 38 million monthly visits.

![Deal Finder Preview](https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800)

## ✨ Features

### 🎯 Smart Deal Finding
- **AI-Powered Deal Scoring**: Automatically analyzes prices and ranks deals from 0-100%
- **Price Comparison**: Compares each listing against similar items to identify bargains
- **Great Deal Detection**: Instantly highlights items priced significantly below average
- **Market Statistics**: See average, minimum, and maximum prices at a glance

### 🔍 Advanced Search
- **Multi-Category Support**: Torget (marketplace), Cars, Real Estate, Motorcycles, Boats
- **Comprehensive Filters**:
  - Price range (min/max in NOK)
  - Item condition (New, As New, Used, For Parts)
  - Location (All Norwegian counties)
  - Publication date (24h, 3 days, 7 days, etc.)
  - Private sellers only
  - Items with images
  - Shipping available (Fiks Ferdig)
- **Flexible Sorting**: By relevance, price (low-high/high-low), or date

### 💾 Save & Organize
- **Saved Searches**: Store your frequently used search criteria
- **Favorites**: Bookmark interesting listings for later
- **Quick Load**: One-click to run saved searches

### 📊 Export Options
- **CSV Export**: Full data export for spreadsheet analysis
- **PDF Reports**: Professional reports with deal scores and statistics
- **Print View**: Optimized print layout for physical records

### 🎨 Stunning UI
- **Modern Dark Theme**: Easy on the eyes with midnight aurora aesthetics
- **Glassmorphism Design**: Beautiful frosted glass effects
- **Smooth Animations**: Delightful micro-interactions and transitions
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile
- **Real-time Feedback**: Loading states, toast notifications, and progress indicators

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the project**
```bash
cd finn_deal_finder
```

2. **Create a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python app.py
```

5. **Open your browser**
Navigate to `http://localhost:5000`

## 📖 Usage Guide

### Basic Search
1. Enter keywords in the search field (e.g., "iPhone 15", "IKEA sofa")
2. Select a category (Torget for general marketplace)
3. Set any filters you want (price range, condition, etc.)
4. Click "Find Best Deals"
5. Review results sorted by deal quality

### Understanding Deal Scores
- **70-100% (Green)**: 🔥 Great Deal - Significantly below average price
- **50-69% (Yellow)**: 👍 Good Deal - Below average price
- **0-49% (Gray)**: Regular listing - At or above average price

### Saving Searches
1. Configure your search parameters
2. Perform a search
3. Click "Save This Search"
4. Enter a memorable name
5. Access later via "Saved Searches" in the header

### Exporting Results
- **CSV**: Click "Export CSV" for spreadsheet-compatible data
- **PDF**: Click "Export PDF" for a formatted report
- **Print**: Click "Print" for a printer-friendly view

## 🏗️ Project Structure

```
finn_deal_finder/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── data/                 # Stored data (auto-created)
│   ├── saved_searches.json
│   ├── favorites.json
│   └── price_history.json
└── templates/
    ├── index.html        # Main application UI
    └── print.html        # Print-friendly template
```

## 🔧 Configuration

### Search Parameters
You can customize the scraping behavior in `app.py`:

```python
# Maximum pages to scrape (more pages = more results but slower)
max_pages = 3  # Default: 3 pages (~150 items)

# Rate limiting (be respectful to finn.no)
time.sleep(0.5)  # Delay between requests
```

### Categories
All categories are configured in `FINN_CATEGORIES` dictionary in `app.py`. You can add or modify categories as needed.

## 🔒 Legal & Ethical Considerations

This tool is designed for personal use to help find deals on Finn.no. Please:

- **Respect Rate Limits**: The tool includes delays to avoid overwhelming finn.no
- **Personal Use Only**: Don't use for commercial scraping operations
- **Review Terms of Service**: Familiarize yourself with finn.no's terms
- **Don't Resell Data**: Data is for personal comparison only

## 🛠️ Technical Details

### Built With
- **Backend**: Flask (Python web framework)
- **Scraping**: BeautifulSoup4 + Requests
- **PDF Generation**: ReportLab
- **Frontend**: Vanilla JavaScript + Custom CSS
- **Design**: Modern glassmorphism with CSS animations

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/api/search` | POST | Perform a search |
| `/api/saved-searches` | GET/POST | Manage saved searches |
| `/api/favorites` | GET/POST | Manage favorite listings |
| `/api/export/csv` | POST | Export to CSV |
| `/api/export/pdf` | POST | Export to PDF |

## 🐛 Troubleshooting

### "No results found"
- Try broader search terms
- Remove some filters
- Check if finn.no is accessible

### "Connection error"
- Verify internet connection
- finn.no may be temporarily unavailable
- Try again in a few minutes

### Slow performance
- Reduce "Pages to Scan" setting
- Close other browser tabs
- Check your internet speed

## 🔜 Future Enhancements

- [ ] Price alerts for saved searches
- [ ] Historical price tracking
- [ ] Email notifications for new deals
- [ ] Browser extension
- [ ] Mobile app version
- [ ] Price prediction using ML
- [ ] Integration with other Norwegian marketplaces

## 📄 License

This project is for educational and personal use. All data sourced from finn.no belongs to Schibsted/FINN.no.

## 🙏 Acknowledgments

- **Finn.no** - Norway's largest marketplace
- **Font**: Outfit by Rodrigo Fuenzalida
- **Icons**: Font Awesome

---

Made with ❤️ for Norwegian deal hunters

**Happy deal hunting!** 🎉
