#!/usr/bin/env python3
"""
Data Manager Module
Handles saving and loading of search criteria, results, and price history
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path


class DataManager:
    """Manages persistent data storage for the application"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the data manager
        
        Args:
            data_dir: Directory for storing data files
        """
        if data_dir is None:
            # Use user's home directory
            home = Path.home()
            data_dir = home / '.finn_deal_finder'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.searches_file = self.data_dir / 'saved_searches.json'
        self.history_file = self.data_dir / 'price_history.json'
        self.settings_file = self.data_dir / 'settings.json'
        self.db_file = self.data_dir / 'finn_data.db'
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for price history"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finn_id TEXT NOT NULL,
                title TEXT,
                price INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                url TEXT,
                category TEXT,
                location TEXT,
                condition TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finn_id TEXT UNIQUE NOT NULL,
                title TEXT,
                price INTEGER,
                url TEXT,
                category TEXT,
                location TEXT,
                condition TEXT,
                deal_score INTEGER,
                notes TEXT,
                saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_name TEXT,
                search_params TEXT,
                results_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_history_finn_id 
            ON price_history(finn_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
            ON price_history(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
    def load_saved_searches(self) -> List[Dict]:
        """Load saved search criteria from file"""
        if not self.searches_file.exists():
            return []
        
        try:
            with open(self.searches_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading saved searches: {e}")
            return []
            
    def save_searches(self, searches: List[Dict]):
        """Save search criteria to file"""
        try:
            with open(self.searches_file, 'w', encoding='utf-8') as f:
                json.dump(searches, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving searches: {e}")
            raise
            
    def add_saved_search(self, search_data: Dict) -> bool:
        """Add a new saved search"""
        searches = self.load_saved_searches()
        
        # Add timestamp if not present
        if 'saved_at' not in search_data:
            search_data['saved_at'] = datetime.now().isoformat()
        
        # Generate ID if not present
        if 'id' not in search_data:
            search_data['id'] = f"search_{len(searches) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        searches.append(search_data)
        self.save_searches(searches)
        return True
        
    def delete_saved_search(self, index: int) -> bool:
        """Delete a saved search by index"""
        searches = self.load_saved_searches()
        
        if 0 <= index < len(searches):
            del searches[index]
            self.save_searches(searches)
            return True
        
        return False
        
    def update_saved_search(self, index: int, search_data: Dict) -> bool:
        """Update an existing saved search"""
        searches = self.load_saved_searches()
        
        if 0 <= index < len(searches):
            search_data['updated_at'] = datetime.now().isoformat()
            searches[index] = search_data
            self.save_searches(searches)
            return True
        
        return False
        
    def save_price_history(self, items: List[Dict]):
        """Save price history for items to database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        for item in items:
            try:
                cursor.execute('''
                    INSERT INTO price_history 
                    (finn_id, title, price, url, category, location, condition)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.get('id', ''),
                    item.get('title', ''),
                    item.get('price', 0),
                    item.get('url', ''),
                    item.get('category', ''),
                    item.get('location', ''),
                    item.get('condition', '')
                ))
            except sqlite3.Error as e:
                print(f"Error saving price history for {item.get('id')}: {e}")
        
        conn.commit()
        conn.close()
        
    def get_price_history(self, finn_id: str) -> List[Dict]:
        """Get price history for a specific item"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT price, timestamp, title, location, condition
            FROM price_history
            WHERE finn_id = ?
            ORDER BY timestamp DESC
        ''', (finn_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'price': row[0],
                'timestamp': row[1],
                'title': row[2],
                'location': row[3],
                'condition': row[4]
            }
            for row in rows
        ]
        
    def get_price_trends(self, category: str = None, days: int = 30) -> Dict:
        """Get price trends for a category over time"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT DATE(timestamp) as date, AVG(price) as avg_price, 
                       COUNT(*) as count, MIN(price) as min_price, MAX(price) as max_price
                FROM price_history
                WHERE category = ? 
                AND timestamp >= date('now', ?)
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (category, f'-{days} days'))
        else:
            cursor.execute('''
                SELECT DATE(timestamp) as date, AVG(price) as avg_price,
                       COUNT(*) as count, MIN(price) as min_price, MAX(price) as max_price
                FROM price_history
                WHERE timestamp >= date('now', ?)
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (f'-{days} days',))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            'dates': [row[0] for row in rows],
            'avg_prices': [row[1] for row in rows],
            'counts': [row[2] for row in rows],
            'min_prices': [row[3] for row in rows],
            'max_prices': [row[4] for row in rows]
        }
        
    def save_item(self, item: Dict) -> bool:
        """Save/bookmark an item for tracking"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO saved_items
                (finn_id, title, price, url, category, location, condition, deal_score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('id', ''),
                item.get('title', ''),
                item.get('price', 0),
                item.get('url', ''),
                item.get('category', ''),
                item.get('location', ''),
                item.get('condition', ''),
                item.get('deal_score', 0),
                item.get('notes', '')
            ))
            
            conn.commit()
            success = True
        except sqlite3.Error as e:
            print(f"Error saving item: {e}")
            success = False
        finally:
            conn.close()
        
        return success
        
    def get_saved_items(self) -> List[Dict]:
        """Get all saved/bookmarked items"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT finn_id, title, price, url, category, location, 
                   condition, deal_score, notes, saved_at, last_updated
            FROM saved_items
            ORDER BY saved_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'price': row[2],
                'url': row[3],
                'category': row[4],
                'location': row[5],
                'condition': row[6],
                'deal_score': row[7],
                'notes': row[8],
                'saved_at': row[9],
                'last_updated': row[10]
            }
            for row in rows
        ]
        
    def delete_saved_item(self, finn_id: str) -> bool:
        """Delete a saved item"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM saved_items WHERE finn_id = ?', (finn_id,))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting item: {e}")
            success = False
        finally:
            conn.close()
        
        return success
        
    def save_search_results(self, name: str, params: Dict, results: List[Dict]) -> bool:
        """Save search results for later reference"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO search_results (search_name, search_params, results_json)
                VALUES (?, ?, ?)
            ''', (
                name,
                json.dumps(params, ensure_ascii=False),
                json.dumps(results, ensure_ascii=False)
            ))
            
            conn.commit()
            success = True
        except sqlite3.Error as e:
            print(f"Error saving search results: {e}")
            success = False
        finally:
            conn.close()
        
        return success
        
    def get_search_results(self, limit: int = 10) -> List[Dict]:
        """Get recent search results"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, search_name, search_params, results_json, created_at
            FROM search_results
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            try:
                results.append({
                    'id': row[0],
                    'name': row[1],
                    'params': json.loads(row[2]),
                    'results': json.loads(row[3]),
                    'created_at': row[4]
                })
            except json.JSONDecodeError:
                continue
        
        return results
        
    def load_settings(self) -> Dict:
        """Load application settings"""
        if not self.settings_file.exists():
            return self._get_default_settings()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults for any missing keys
                return {**self._get_default_settings(), **settings}
        except (json.JSONDecodeError, IOError):
            return self._get_default_settings()
            
    def save_settings(self, settings: Dict):
        """Save application settings"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving settings: {e}")
            raise
            
    def _get_default_settings(self) -> Dict:
        """Get default application settings"""
        return {
            'theme': 'dark',
            'language': 'no',
            'max_concurrent_requests': 5,
            'request_delay_min': 0.5,
            'request_delay_max': 1.5,
            'default_max_results': 50,
            'default_deal_threshold': 70,
            'auto_save_results': True,
            'notifications_enabled': False,
            'proxy_enabled': False,
            'proxy_url': '',
            'export_directory': str(Path.home() / 'Downloads'),
        }
        
    def cleanup_old_data(self, days: int = 90):
        """Clean up old price history data"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM price_history
                WHERE timestamp < date('now', ?)
            ''', (f'-{days} days',))
            
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"Cleaned up {deleted_count} old price history records")
        except sqlite3.Error as e:
            print(f"Error during cleanup: {e}")
        finally:
            conn.close()
            
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            cursor.execute('SELECT COUNT(*) FROM price_history')
            stats['price_history_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM saved_items')
            stats['saved_items_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM search_results')
            stats['search_results_count'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT finn_id) FROM price_history')
            stats['unique_items_tracked'] = cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            print(f"Error getting statistics: {e}")
        finally:
            conn.close()
        
        return stats
