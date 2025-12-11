#!/usr/bin/env python3
"""
FINN.no Deal Finder Pro
A beautiful, modern web scraper for finding the best deals on FINN.no
Created for Paulo - Data Center Operations Manager
"""

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import json
import os
import threading
from datetime import datetime
import webbrowser
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import filedialog, messagebox
import sys

# Import our custom modules
from scraper import FinnScraper
from deal_analyzer import DealAnalyzer
from data_manager import DataManager
from export_manager import ExportManager

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernGradientFrame(ctk.CTkFrame):
    """Custom frame with gradient background effect"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")

class AnimatedButton(ctk.CTkButton):
    """Button with hover animation effect"""
    def __init__(self, master, **kwargs):
        self.original_color = kwargs.get('fg_color', '#6366f1')
        self.hover_color = kwargs.get('hover_color', '#818cf8')
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        
    def _on_enter(self, event):
        self.configure(fg_color=self.hover_color)
        
    def _on_leave(self, event):
        self.configure(fg_color=self.original_color)

class FinnDealFinderApp(ctk.CTk):
    """Main application class for FINN.no Deal Finder"""
    
    # Color scheme - Modern dark theme with vibrant accents
    COLORS = {
        'bg_primary': '#0f0f1a',
        'bg_secondary': '#1a1a2e',
        'bg_tertiary': '#16213e',
        'accent_primary': '#6366f1',
        'accent_secondary': '#8b5cf6',
        'accent_success': '#10b981',
        'accent_warning': '#f59e0b',
        'accent_danger': '#ef4444',
        'accent_info': '#06b6d4',
        'text_primary': '#f8fafc',
        'text_secondary': '#94a3b8',
        'text_muted': '#64748b',
        'border': '#334155',
        'gradient_start': '#6366f1',
        'gradient_end': '#8b5cf6',
        'card_bg': '#1e1e32',
        'highlight': '#fbbf24',
    }
    
    # FINN.no Categories
    CATEGORIES = {
        'Torget (Marketplace)': {
            'url_base': 'https://www.finn.no/bap/forsale/search.html',
            'subcategories': {
                'Alle kategorier': '',
                'Antikviteter og kunst': 'category=1.60',
                'Dyr og utstyr': 'category=1.61',
                'Elektronikk og hvitevarer': 'category=1.93',
                'Friluftsliv og sport': 'category=1.94',
                'Hage og utemiljø': 'category=1.95',
                'Hobby og underholdning': 'category=1.96',
                'Hus og hjem': 'category=1.69',
                'Klær, kosmetikk og tilbehør': 'category=1.70',
                'Bil-, MC- og båtutstyr': 'category=1.90',
                'Barn og baby': 'category=1.73',
                'Næring og industri': 'category=1.97',
                'Annet': 'category=1.98',
            }
        },
        'Bil (Cars)': {
            'url_base': 'https://www.finn.no/car/used/search.html',
            'subcategories': {
                'Alle biler': '',
                'Personbil': 'body_type=1',
                'Stasjonsvogn': 'body_type=2',
                'SUV/Offroad': 'body_type=4',
                'Småbil': 'body_type=6',
                'Cabriolet': 'body_type=3',
            }
        },
        'Eiendom (Real Estate)': {
            'url_base': 'https://www.finn.no/realestate/homes/search.html',
            'subcategories': {
                'Alle boliger': '',
                'Leilighet': 'property_type=1',
                'Enebolig': 'property_type=2',
                'Rekkehus': 'property_type=3',
                'Tomannsbolig': 'property_type=4',
            }
        },
        'MC': {
            'url_base': 'https://www.finn.no/mc/used/search.html',
            'subcategories': {
                'Alle motorsykler': '',
                'Sport': 'body_type=1',
                'Touring': 'body_type=2',
                'Custom/Chopper': 'body_type=3',
            }
        },
        'Båt (Boats)': {
            'url_base': 'https://www.finn.no/boat/used/search.html',
            'subcategories': {
                'Alle båter': '',
                'Motorbåt': 'boat_type=1',
                'Seilbåt': 'boat_type=2',
                'RIB': 'boat_type=3',
            }
        },
    }
    
    # Norwegian Regions
    LOCATIONS = {
        'Hele Norge': '',
        'Oslo': 'location=0.20061',
        'Bergen': 'location=0.20220',
        'Trondheim': 'location=0.20016',
        'Stavanger': 'location=0.20012',
        'Kristiansand': 'location=0.20001',
        'Tromsø': 'location=0.20019',
        'Akershus': 'location=0.20003',
        'Rogaland': 'location=0.20012',
        'Hordaland': 'location=0.20007',
        'Vestland': 'location=0.20046',
        'Trøndelag': 'location=0.20016',
        'Nordland': 'location=0.20018',
        'Møre og Romsdal': 'location=0.20015',
        'Innlandet': 'location=0.20004',
        'Vestfold og Telemark': 'location=0.20038',
        'Agder': 'location=0.20001',
        'Viken': 'location=0.22030',
    }
    
    # Condition filters
    CONDITIONS = {
        'Alle tilstander': '',
        'Ny (New)': 'condition=1',
        'Som ny (Like New)': 'condition=2',
        'Pent brukt (Lightly Used)': 'condition=3',
        'Brukt (Used)': 'condition=4',
        'Til reparasjon (For Repair)': 'condition=5',
    }
    
    # Sorting options
    SORT_OPTIONS = {
        'Nyeste først (Newest)': 'sort=PUBLISHED_DESC',
        'Pris lav-høy (Price Low-High)': 'sort=PRICE_ASC',
        'Pris høy-lav (Price High-Low)': 'sort=PRICE_DESC',
        'Eldste først (Oldest)': 'sort=PUBLISHED_ASC',
    }
    
    def __init__(self):
        super().__init__()
        
        # Initialize managers
        self.data_manager = DataManager()
        self.scraper = FinnScraper()
        self.analyzer = DealAnalyzer()
        self.export_manager = ExportManager()
        
        # Application state
        self.current_results = []
        self.saved_searches = []
        self.is_scraping = False
        self.progress_value = 0
        
        # Configure window
        self.title("🔍 FINN.no Deal Finder Pro")
        self.geometry("1600x950")
        self.minsize(1400, 800)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(0, weight=1)
        
        # Set window icon and appearance
        self.configure(fg_color=self.COLORS['bg_primary'])
        
        # Build UI
        self._create_sidebar()
        self._create_main_content()
        self._load_saved_searches()
        
        # Bind keyboard shortcuts
        self.bind('<Control-s>', lambda e: self._save_current_search())
        self.bind('<Control-e>', lambda e: self._export_results())
        self.bind('<F5>', lambda e: self._start_search())
        self.bind('<Escape>', lambda e: self._stop_search())
        
    def _create_sidebar(self):
        """Create the left sidebar with search filters"""
        # Sidebar container
        self.sidebar = ctk.CTkFrame(
            self,
            width=380,
            corner_radius=0,
            fg_color=self.COLORS['bg_secondary']
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Scrollable frame for sidebar content
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_fg_color=self.COLORS['bg_tertiary'],
            scrollbar_button_color=self.COLORS['accent_primary']
        )
        self.sidebar_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Logo and title section
        self._create_logo_section()
        
        # Search filters section
        self._create_filter_section()
        
        # Saved searches section
        self._create_saved_searches_section()
        
    def _create_logo_section(self):
        """Create the logo and branding section"""
        logo_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        logo_frame.pack(fill="x", pady=(10, 25))
        
        # App title with gradient effect simulation
        title_label = ctk.CTkLabel(
            logo_frame,
            text="🏆 FINN Deal Finder",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.COLORS['text_primary']
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            logo_frame,
            text="Find the Best Deals in Norway",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.COLORS['text_secondary']
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Decorative line
        line_frame = ctk.CTkFrame(
            logo_frame,
            height=3,
            fg_color=self.COLORS['accent_primary'],
            corner_radius=2
        )
        line_frame.pack(fill="x", pady=(15, 0), padx=40)
        
    def _create_filter_section(self):
        """Create the search filters section"""
        # Section header
        filter_header = ctk.CTkLabel(
            self.sidebar_scroll,
            text="🎯 Search Filters",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.COLORS['text_primary'],
            anchor="w"
        )
        filter_header.pack(fill="x", pady=(10, 15))
        
        # Search keyword
        self._create_filter_label("🔤 Search Keywords")
        self.search_entry = ctk.CTkEntry(
            self.sidebar_scroll,
            placeholder_text="e.g., iPhone 15, Gaming PC, MacBook...",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            border_color=self.COLORS['border'],
            text_color=self.COLORS['text_primary']
        )
        self.search_entry.pack(fill="x", pady=(0, 15))
        
        # Category selection
        self._create_filter_label("📁 Market Category")
        self.category_var = ctk.StringVar(value="Torget (Marketplace)")
        self.category_menu = ctk.CTkOptionMenu(
            self.sidebar_scroll,
            variable=self.category_var,
            values=list(self.CATEGORIES.keys()),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent_primary'],
            button_hover_color=self.COLORS['accent_secondary'],
            dropdown_fg_color=self.COLORS['bg_tertiary'],
            command=self._on_category_change
        )
        self.category_menu.pack(fill="x", pady=(0, 15))
        
        # Subcategory selection
        self._create_filter_label("📂 Subcategory")
        self.subcategory_var = ctk.StringVar(value="Alle kategorier")
        self.subcategory_menu = ctk.CTkOptionMenu(
            self.sidebar_scroll,
            variable=self.subcategory_var,
            values=list(self.CATEGORIES['Torget (Marketplace)']['subcategories'].keys()),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent_primary'],
            button_hover_color=self.COLORS['accent_secondary'],
            dropdown_fg_color=self.COLORS['bg_tertiary']
        )
        self.subcategory_menu.pack(fill="x", pady=(0, 15))
        
        # Location selection
        self._create_filter_label("📍 Location")
        self.location_var = ctk.StringVar(value="Hele Norge")
        self.location_menu = ctk.CTkOptionMenu(
            self.sidebar_scroll,
            variable=self.location_var,
            values=list(self.LOCATIONS.keys()),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent_primary'],
            button_hover_color=self.COLORS['accent_secondary'],
            dropdown_fg_color=self.COLORS['bg_tertiary']
        )
        self.location_menu.pack(fill="x", pady=(0, 15))
        
        # Condition selection
        self._create_filter_label("✨ Condition")
        self.condition_var = ctk.StringVar(value="Alle tilstander")
        self.condition_menu = ctk.CTkOptionMenu(
            self.sidebar_scroll,
            variable=self.condition_var,
            values=list(self.CONDITIONS.keys()),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent_primary'],
            button_hover_color=self.COLORS['accent_secondary'],
            dropdown_fg_color=self.COLORS['bg_tertiary']
        )
        self.condition_menu.pack(fill="x", pady=(0, 15))
        
        # Price range
        self._create_filter_label("💰 Price Range (NOK)")
        price_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        price_frame.pack(fill="x", pady=(0, 15))
        
        self.price_min_entry = ctk.CTkEntry(
            price_frame,
            placeholder_text="Min price",
            height=45,
            width=150,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            border_color=self.COLORS['border'],
            text_color=self.COLORS['text_primary']
        )
        self.price_min_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        dash_label = ctk.CTkLabel(
            price_frame,
            text="—",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_secondary']
        )
        dash_label.pack(side="left", padx=5)
        
        self.price_max_entry = ctk.CTkEntry(
            price_frame,
            placeholder_text="Max price",
            height=45,
            width=150,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            border_color=self.COLORS['border'],
            text_color=self.COLORS['text_primary']
        )
        self.price_max_entry.pack(side="right", expand=True, fill="x", padx=(5, 0))
        
        # Sort option
        self._create_filter_label("📊 Sort By")
        self.sort_var = ctk.StringVar(value="Nyeste først (Newest)")
        self.sort_menu = ctk.CTkOptionMenu(
            self.sidebar_scroll,
            variable=self.sort_var,
            values=list(self.SORT_OPTIONS.keys()),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent_primary'],
            button_hover_color=self.COLORS['accent_secondary'],
            dropdown_fg_color=self.COLORS['bg_tertiary']
        )
        self.sort_menu.pack(fill="x", pady=(0, 15))
        
        # Max results
        self._create_filter_label("📋 Max Results")
        self.max_results_var = ctk.IntVar(value=50)
        self.max_results_slider = ctk.CTkSlider(
            self.sidebar_scroll,
            from_=10,
            to=200,
            number_of_steps=19,
            variable=self.max_results_var,
            fg_color=self.COLORS['bg_tertiary'],
            progress_color=self.COLORS['accent_primary'],
            button_color=self.COLORS['accent_secondary'],
            command=self._update_max_results_label
        )
        self.max_results_slider.pack(fill="x", pady=(0, 5))
        
        self.max_results_label = ctk.CTkLabel(
            self.sidebar_scroll,
            text="50 results",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        self.max_results_label.pack(anchor="e", pady=(0, 20))
        
        # Deal threshold
        self._create_filter_label("🎯 Deal Score Threshold")
        self.deal_threshold_var = ctk.IntVar(value=70)
        self.deal_threshold_slider = ctk.CTkSlider(
            self.sidebar_scroll,
            from_=0,
            to=100,
            number_of_steps=20,
            variable=self.deal_threshold_var,
            fg_color=self.COLORS['bg_tertiary'],
            progress_color=self.COLORS['accent_success'],
            button_color=self.COLORS['accent_success'],
            command=self._update_threshold_label
        )
        self.deal_threshold_slider.pack(fill="x", pady=(0, 5))
        
        self.deal_threshold_label = ctk.CTkLabel(
            self.sidebar_scroll,
            text="Show deals scoring 70%+ (Good deals)",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['accent_success']
        )
        self.deal_threshold_label.pack(anchor="e", pady=(0, 25))
        
        # Search buttons
        button_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 20))
        
        self.search_button = ctk.CTkButton(
            button_frame,
            text="🔍 Find Deals",
            height=55,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            fg_color=self.COLORS['accent_primary'],
            hover_color=self.COLORS['accent_secondary'],
            corner_radius=12,
            command=self._start_search
        )
        self.search_button.pack(fill="x", pady=(0, 10))
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹ Stop Search",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['accent_danger'],
            hover_color='#dc2626',
            corner_radius=10,
            command=self._stop_search,
            state="disabled"
        )
        self.stop_button.pack(fill="x", pady=(0, 10))
        
        self.save_search_button = ctk.CTkButton(
            button_frame,
            text="💾 Save Search Criteria",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['bg_tertiary'],
            hover_color=self.COLORS['border'],
            border_color=self.COLORS['accent_primary'],
            border_width=2,
            corner_radius=10,
            command=self._save_current_search
        )
        self.save_search_button.pack(fill="x")
        
    def _create_filter_label(self, text):
        """Create a filter section label"""
        label = ctk.CTkLabel(
            self.sidebar_scroll,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.COLORS['text_secondary'],
            anchor="w"
        )
        label.pack(fill="x", pady=(5, 8))
        
    def _create_saved_searches_section(self):
        """Create the saved searches section"""
        # Divider
        divider = ctk.CTkFrame(
            self.sidebar_scroll,
            height=2,
            fg_color=self.COLORS['border']
        )
        divider.pack(fill="x", pady=20)
        
        # Section header
        saved_header = ctk.CTkLabel(
            self.sidebar_scroll,
            text="💾 Saved Searches",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.COLORS['text_primary'],
            anchor="w"
        )
        saved_header.pack(fill="x", pady=(0, 15))
        
        # Saved searches container
        self.saved_searches_frame = ctk.CTkFrame(
            self.sidebar_scroll,
            fg_color="transparent"
        )
        self.saved_searches_frame.pack(fill="x")
        
    def _create_main_content(self):
        """Create the main content area"""
        # Main container
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLORS['bg_primary'],
            corner_radius=0
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header with stats
        self._create_header()
        
        # Tabview for results
        self._create_tabview()
        
        # Footer with export options
        self._create_footer()
        
    def _create_header(self):
        """Create the header with statistics"""
        header_frame = ctk.CTkFrame(
            self.main_frame,
            height=120,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=0
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        # Stats cards container
        stats_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_container.pack(fill="both", expand=True, padx=25, pady=15)
        
        # Progress bar (initially hidden)
        self.progress_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=8,
            fg_color=self.COLORS['bg_tertiary'],
            progress_color=self.COLORS['accent_primary'],
            corner_radius=4
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready to search...",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        self.progress_label.pack(anchor="e", pady=(5, 0))
        
        # Stats row
        stats_row = ctk.CTkFrame(stats_container, fg_color="transparent")
        stats_row.pack(fill="x")
        
        # Total Results stat
        self.stat_total = self._create_stat_card(
            stats_row,
            "📊 Total Results",
            "0",
            self.COLORS['accent_primary']
        )
        self.stat_total.pack(side="left", padx=(0, 15))
        
        # Great Deals stat
        self.stat_deals = self._create_stat_card(
            stats_row,
            "🔥 Hot Deals",
            "0",
            self.COLORS['accent_danger']
        )
        self.stat_deals.pack(side="left", padx=15)
        
        # Average Price stat
        self.stat_avg_price = self._create_stat_card(
            stats_row,
            "💰 Avg. Price",
            "0 kr",
            self.COLORS['accent_success']
        )
        self.stat_avg_price.pack(side="left", padx=15)
        
        # Best Deal stat
        self.stat_best_deal = self._create_stat_card(
            stats_row,
            "🏆 Best Deal Score",
            "—",
            self.COLORS['highlight']
        )
        self.stat_best_deal.pack(side="left", padx=15)
        
        # Potential Savings stat
        self.stat_savings = self._create_stat_card(
            stats_row,
            "💵 Potential Savings",
            "0 kr",
            self.COLORS['accent_info']
        )
        self.stat_savings.pack(side="left", padx=15)
        
    def _create_stat_card(self, parent, title, value, color):
        """Create a statistics card"""
        card = ctk.CTkFrame(
            parent,
            width=180,
            height=70,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=color
        )
        card.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_secondary']
        )
        title_label.pack(pady=(10, 2))
        
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=color
        )
        value_label.pack()
        
        # Store reference for updates
        card.value_label = value_label
        
        return card
        
    def _create_tabview(self):
        """Create the tabview for different result views"""
        self.tabview = ctk.CTkTabview(
            self.main_frame,
            fg_color=self.COLORS['bg_primary'],
            segmented_button_fg_color=self.COLORS['bg_secondary'],
            segmented_button_selected_color=self.COLORS['accent_primary'],
            segmented_button_selected_hover_color=self.COLORS['accent_secondary'],
            segmented_button_unselected_color=self.COLORS['bg_tertiary'],
            segmented_button_unselected_hover_color=self.COLORS['border'],
            text_color=self.COLORS['text_primary']
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 0))
        
        # Add tabs
        self.tab_all = self.tabview.add("📋 All Results")
        self.tab_deals = self.tabview.add("🔥 Hot Deals")
        self.tab_compare = self.tabview.add("⚖️ Price Comparison")
        self.tab_history = self.tabview.add("📈 Price History")
        
        # Configure tabs
        for tab in [self.tab_all, self.tab_deals, self.tab_compare, self.tab_history]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        
        # Create scrollable frames for each tab
        self._create_all_results_tab()
        self._create_deals_tab()
        self._create_compare_tab()
        self._create_history_tab()
        
    def _create_all_results_tab(self):
        """Create the all results tab content"""
        self.all_results_scroll = ctk.CTkScrollableFrame(
            self.tab_all,
            fg_color="transparent",
            scrollbar_fg_color=self.COLORS['bg_tertiary'],
            scrollbar_button_color=self.COLORS['accent_primary']
        )
        self.all_results_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Placeholder
        self.all_results_placeholder = ctk.CTkLabel(
            self.all_results_scroll,
            text="🔍\n\nNo results yet.\nConfigure your search filters and click 'Find Deals' to start!",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        self.all_results_placeholder.pack(expand=True, pady=100)
        
    def _create_deals_tab(self):
        """Create the hot deals tab content"""
        self.deals_scroll = ctk.CTkScrollableFrame(
            self.tab_deals,
            fg_color="transparent",
            scrollbar_fg_color=self.COLORS['bg_tertiary'],
            scrollbar_button_color=self.COLORS['accent_danger']
        )
        self.deals_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Placeholder
        self.deals_placeholder = ctk.CTkLabel(
            self.deals_scroll,
            text="🔥\n\nHot deals will appear here!\nWe'll highlight items priced significantly below average.",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        self.deals_placeholder.pack(expand=True, pady=100)
        
    def _create_compare_tab(self):
        """Create the price comparison tab content"""
        self.compare_scroll = ctk.CTkScrollableFrame(
            self.tab_compare,
            fg_color="transparent",
            scrollbar_fg_color=self.COLORS['bg_tertiary'],
            scrollbar_button_color=self.COLORS['accent_info']
        )
        self.compare_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Placeholder
        self.compare_placeholder = ctk.CTkLabel(
            self.compare_scroll,
            text="⚖️\n\nPrice comparisons will appear here!\nSimilar products will be grouped for easy comparison.",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        self.compare_placeholder.pack(expand=True, pady=100)
        
    def _create_history_tab(self):
        """Create the price history tab content"""
        self.history_scroll = ctk.CTkScrollableFrame(
            self.tab_history,
            fg_color="transparent",
            scrollbar_fg_color=self.COLORS['bg_tertiary'],
            scrollbar_button_color=self.COLORS['accent_success']
        )
        self.history_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Placeholder
        self.history_placeholder = ctk.CTkLabel(
            self.history_scroll,
            text="📈\n\nPrice history tracking coming soon!\nTrack prices over time to find the best moment to buy.",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        self.history_placeholder.pack(expand=True, pady=100)
        
    def _create_footer(self):
        """Create the footer with export options"""
        footer_frame = ctk.CTkFrame(
            self.main_frame,
            height=70,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=0
        )
        footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer_frame.grid_propagate(False)
        
        # Footer content
        footer_content = ctk.CTkFrame(footer_frame, fg_color="transparent")
        footer_content.pack(fill="both", expand=True, padx=25, pady=12)
        
        # Export buttons
        export_frame = ctk.CTkFrame(footer_content, fg_color="transparent")
        export_frame.pack(side="left")
        
        self.export_csv_btn = ctk.CTkButton(
            export_frame,
            text="📄 Export CSV",
            width=130,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS['bg_tertiary'],
            hover_color=self.COLORS['border'],
            corner_radius=8,
            command=lambda: self._export_results('csv')
        )
        self.export_csv_btn.pack(side="left", padx=(0, 10))
        
        self.export_excel_btn = ctk.CTkButton(
            export_frame,
            text="📊 Export Excel",
            width=130,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS['bg_tertiary'],
            hover_color=self.COLORS['border'],
            corner_radius=8,
            command=lambda: self._export_results('excel')
        )
        self.export_excel_btn.pack(side="left", padx=(0, 10))
        
        self.export_json_btn = ctk.CTkButton(
            export_frame,
            text="🔗 Export JSON",
            width=130,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS['bg_tertiary'],
            hover_color=self.COLORS['border'],
            corner_radius=8,
            command=lambda: self._export_results('json')
        )
        self.export_json_btn.pack(side="left", padx=(0, 10))
        
        self.print_btn = ctk.CTkButton(
            export_frame,
            text="🖨️ Print Report",
            width=130,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS['accent_info'],
            hover_color='#0891b2',
            corner_radius=8,
            command=self._print_results
        )
        self.print_btn.pack(side="left", padx=(0, 10))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            footer_content,
            text="Ready • FINN.no Deal Finder Pro v1.0",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        )
        self.status_label.pack(side="right")
        
    def _on_category_change(self, value):
        """Handle category change event"""
        category_data = self.CATEGORIES.get(value, {})
        subcategories = list(category_data.get('subcategories', {}).keys())
        
        self.subcategory_menu.configure(values=subcategories)
        self.subcategory_var.set(subcategories[0] if subcategories else '')
        
    def _update_max_results_label(self, value):
        """Update max results label"""
        self.max_results_label.configure(text=f"{int(value)} results")
        
    def _update_threshold_label(self, value):
        """Update threshold label"""
        score = int(value)
        if score >= 80:
            text = f"Show deals scoring {score}%+ (Excellent deals)"
            color = self.COLORS['accent_success']
        elif score >= 60:
            text = f"Show deals scoring {score}%+ (Good deals)"
            color = self.COLORS['accent_warning']
        else:
            text = f"Show deals scoring {score}%+ (All deals)"
            color = self.COLORS['text_secondary']
        
        self.deal_threshold_label.configure(text=text, text_color=color)
        
    def _load_saved_searches(self):
        """Load saved searches from file"""
        self.saved_searches = self.data_manager.load_saved_searches()
        self._update_saved_searches_ui()
        
    def _update_saved_searches_ui(self):
        """Update the saved searches UI"""
        # Clear existing widgets
        for widget in self.saved_searches_frame.winfo_children():
            widget.destroy()
            
        if not self.saved_searches:
            empty_label = ctk.CTkLabel(
                self.saved_searches_frame,
                text="No saved searches yet.\nSave your first search!",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            empty_label.pack(pady=20)
            return
            
        for i, search in enumerate(self.saved_searches):
            self._create_saved_search_card(search, i)
            
    def _create_saved_search_card(self, search: dict, index: int):
        """Create a saved search card"""
        card = ctk.CTkFrame(
            self.saved_searches_frame,
            fg_color=self.COLORS['card_bg'],
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS['border']
        )
        card.pack(fill="x", pady=(0, 8))
        
        # Card content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=10)
        
        # Search name
        name_label = ctk.CTkLabel(
            content,
            text=search.get('name', f'Search {index + 1}'),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS['text_primary'],
            anchor="w"
        )
        name_label.pack(fill="x")
        
        # Search details
        details = f"{search.get('category', 'N/A')} • {search.get('location', 'Hele Norge')}"
        if search.get('keyword'):
            details = f"\"{search.get('keyword')}\" • {details}"
        
        details_label = ctk.CTkLabel(
            content,
            text=details,
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_secondary'],
            anchor="w"
        )
        details_label.pack(fill="x", pady=(2, 5))
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        load_btn = ctk.CTkButton(
            btn_frame,
            text="Load",
            width=60,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=self.COLORS['accent_primary'],
            hover_color=self.COLORS['accent_secondary'],
            corner_radius=6,
            command=lambda s=search: self._load_saved_search(s)
        )
        load_btn.pack(side="left", padx=(0, 5))
        
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="✕",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=self.COLORS['accent_danger'],
            hover_color='#dc2626',
            corner_radius=6,
            command=lambda i=index: self._delete_saved_search(i)
        )
        delete_btn.pack(side="left")
        
    def _save_current_search(self):
        """Save the current search criteria"""
        # Create dialog
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this search:",
            title="Save Search"
        )
        name = dialog.get_input()
        
        if not name:
            return
            
        search_data = {
            'name': name,
            'keyword': self.search_entry.get(),
            'category': self.category_var.get(),
            'subcategory': self.subcategory_var.get(),
            'location': self.location_var.get(),
            'condition': self.condition_var.get(),
            'price_min': self.price_min_entry.get(),
            'price_max': self.price_max_entry.get(),
            'sort': self.sort_var.get(),
            'max_results': self.max_results_var.get(),
            'deal_threshold': self.deal_threshold_var.get(),
            'saved_at': datetime.now().isoformat()
        }
        
        self.saved_searches.append(search_data)
        self.data_manager.save_searches(self.saved_searches)
        self._update_saved_searches_ui()
        
        self.status_label.configure(text=f"✅ Search '{name}' saved successfully!")
        
    def _load_saved_search(self, search: dict):
        """Load a saved search into the filters"""
        self.search_entry.delete(0, 'end')
        self.search_entry.insert(0, search.get('keyword', ''))
        
        self.category_var.set(search.get('category', 'Torget (Marketplace)'))
        self._on_category_change(search.get('category', 'Torget (Marketplace)'))
        self.subcategory_var.set(search.get('subcategory', ''))
        self.location_var.set(search.get('location', 'Hele Norge'))
        self.condition_var.set(search.get('condition', 'Alle tilstander'))
        
        self.price_min_entry.delete(0, 'end')
        self.price_min_entry.insert(0, search.get('price_min', ''))
        
        self.price_max_entry.delete(0, 'end')
        self.price_max_entry.insert(0, search.get('price_max', ''))
        
        self.sort_var.set(search.get('sort', 'Nyeste først (Newest)'))
        self.max_results_var.set(search.get('max_results', 50))
        self.deal_threshold_var.set(search.get('deal_threshold', 70))
        
        self._update_max_results_label(search.get('max_results', 50))
        self._update_threshold_label(search.get('deal_threshold', 70))
        
        self.status_label.configure(text=f"✅ Loaded search: {search.get('name', 'Unknown')}")
        
    def _delete_saved_search(self, index: int):
        """Delete a saved search"""
        if 0 <= index < len(self.saved_searches):
            name = self.saved_searches[index].get('name', 'Search')
            del self.saved_searches[index]
            self.data_manager.save_searches(self.saved_searches)
            self._update_saved_searches_ui()
            self.status_label.configure(text=f"🗑️ Deleted search: {name}")
            
    def _start_search(self):
        """Start the search process"""
        if self.is_scraping:
            return
            
        self.is_scraping = True
        self.search_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Initializing search...")
        
        # Build search parameters
        search_params = self._build_search_params()
        
        # Start search in background thread
        thread = threading.Thread(
            target=self._run_search,
            args=(search_params,),
            daemon=True
        )
        thread.start()
        
    def _build_search_params(self) -> dict:
        """Build the search parameters from UI"""
        category = self.category_var.get()
        category_data = self.CATEGORIES.get(category, {})
        
        params = {
            'url_base': category_data.get('url_base', ''),
            'keyword': self.search_entry.get(),
            'subcategory': category_data.get('subcategories', {}).get(
                self.subcategory_var.get(), ''
            ),
            'location': self.LOCATIONS.get(self.location_var.get(), ''),
            'condition': self.CONDITIONS.get(self.condition_var.get(), ''),
            'price_min': self.price_min_entry.get(),
            'price_max': self.price_max_entry.get(),
            'sort': self.SORT_OPTIONS.get(self.sort_var.get(), ''),
            'max_results': self.max_results_var.get(),
            'deal_threshold': self.deal_threshold_var.get()
        }
        
        return params
        
    def _run_search(self, params: dict):
        """Run the search (in background thread)"""
        try:
            # Update progress
            self.after(0, lambda: self.progress_label.configure(
                text="Connecting to FINN.no..."
            ))
            self.after(0, lambda: self.progress_bar.set(0.1))
            
            # Perform scraping
            results = self.scraper.search(
                params,
                progress_callback=self._update_progress
            )
            
            if not self.is_scraping:  # Check if stopped
                return
                
            # Analyze deals
            self.after(0, lambda: self.progress_label.configure(
                text="Analyzing deals..."
            ))
            self.after(0, lambda: self.progress_bar.set(0.9))
            
            analyzed_results = self.analyzer.analyze(
                results,
                threshold=params.get('deal_threshold', 70)
            )
            
            # Update UI with results
            self.after(0, lambda: self._display_results(analyzed_results))
            
        except Exception as e:
    self.after(0, lambda err=e: self._show_error(str(err)))
        finally:
            self.after(0, self._search_complete)
            
    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress from scraper"""
        progress = current / total if total > 0 else 0
        self.after(0, lambda: self.progress_bar.set(progress * 0.8 + 0.1))
        self.after(0, lambda: self.progress_label.configure(
            text=f"Scraping... {current}/{total} items {message}"
        ))
        
    def _display_results(self, results: dict):
        """Display the search results"""
        self.current_results = results.get('items', [])
        
        # Update statistics
        self._update_statistics(results)
        
        # Display in All Results tab
        self._populate_all_results(self.current_results)
        
        # Display in Hot Deals tab
        hot_deals = [item for item in self.current_results if item.get('deal_score', 0) >= self.deal_threshold_var.get()]
        self._populate_deals(hot_deals)
        
        # Display in Compare tab
        self._populate_comparisons(results.get('comparisons', {}))
        
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ Found {len(self.current_results)} items, {len(hot_deals)} hot deals!"
        )
        
    def _update_statistics(self, results: dict):
        """Update the statistics cards"""
        items = results.get('items', [])
        stats = results.get('stats', {})
        
        # Update stat cards
        self.stat_total.value_label.configure(text=str(len(items)))
        
        hot_deals = len([i for i in items if i.get('deal_score', 0) >= self.deal_threshold_var.get()])
        self.stat_deals.value_label.configure(text=str(hot_deals))
        
        avg_price = stats.get('avg_price', 0)
        self.stat_avg_price.value_label.configure(text=f"{avg_price:,.0f} kr")
        
        best_score = stats.get('best_deal_score', 0)
        self.stat_best_deal.value_label.configure(text=f"{best_score}%")
        
        savings = stats.get('potential_savings', 0)
        self.stat_savings.value_label.configure(text=f"{savings:,.0f} kr")
        
    def _populate_all_results(self, items: list):
        """Populate the all results tab"""
        # Clear existing
        for widget in self.all_results_scroll.winfo_children():
            widget.destroy()
            
        if not items:
            placeholder = ctk.CTkLabel(
                self.all_results_scroll,
                text="🔍\n\nNo results found.\nTry adjusting your search filters.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            placeholder.pack(expand=True, pady=100)
            return
            
        # Create result cards
        for item in items:
            self._create_result_card(self.all_results_scroll, item)
            
    def _populate_deals(self, items: list):
        """Populate the hot deals tab"""
        # Clear existing
        for widget in self.deals_scroll.winfo_children():
            widget.destroy()
            
        if not items:
            placeholder = ctk.CTkLabel(
                self.deals_scroll,
                text="🔥\n\nNo hot deals found.\nTry lowering the deal threshold or broadening your search.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            placeholder.pack(expand=True, pady=100)
            return
            
        # Sort by deal score
        items.sort(key=lambda x: x.get('deal_score', 0), reverse=True)
        
        for item in items:
            self._create_result_card(self.deals_scroll, item, highlight=True)
            
    def _populate_comparisons(self, comparisons: dict):
        """Populate the comparison tab"""
        # Clear existing
        for widget in self.compare_scroll.winfo_children():
            widget.destroy()
            
        if not comparisons:
            placeholder = ctk.CTkLabel(
                self.compare_scroll,
                text="⚖️\n\nNo comparable items found.\nPrice comparisons require similar items to compare.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            placeholder.pack(expand=True, pady=100)
            return
            
        for group_name, items in comparisons.items():
            self._create_comparison_group(group_name, items)
            
    def _create_result_card(self, parent, item: dict, highlight: bool = False):
        """Create a result card"""
        border_color = self.COLORS['accent_danger'] if highlight else self.COLORS['border']
        
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12,
            border_width=2 if highlight else 1,
            border_color=border_color
        )
        card.pack(fill="x", pady=8, padx=5)
        
        # Card content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)
        
        # Top row: Title and Deal Score
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")
        
        title = item.get('title', 'Unknown Item')
        if len(title) > 60:
            title = title[:60] + "..."
        
        title_label = ctk.CTkLabel(
            top_row,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.COLORS['text_primary'],
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        # Deal score badge
        deal_score = item.get('deal_score', 0)
        if deal_score > 0:
            score_color = self._get_score_color(deal_score)
            score_badge = ctk.CTkFrame(
                top_row,
                fg_color=score_color,
                corner_radius=6,
                width=60,
                height=26
            )
            score_badge.pack(side="right", padx=(10, 0))
            score_badge.pack_propagate(False)
            
            score_label = ctk.CTkLabel(
                score_badge,
                text=f"🔥 {deal_score}%",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            score_label.pack(expand=True)
        
        # Middle row: Details
        details_frame = ctk.CTkFrame(content, fg_color="transparent")
        details_frame.pack(fill="x", pady=(8, 8))
        
        # Price
        price = item.get('price', 0)
        price_text = f"💰 {price:,.0f} kr" if price else "💰 Pris ikke oppgitt"
        price_label = ctk.CTkLabel(
            details_frame,
            text=price_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['accent_success']
        )
        price_label.pack(side="left")
        
        # Average price comparison
        avg_price = item.get('avg_price', 0)
        if avg_price > 0 and price > 0:
            diff = avg_price - price
            if diff > 0:
                comparison_text = f"  📉 {diff:,.0f} kr under avg"
                comparison_color = self.COLORS['accent_success']
            else:
                comparison_text = f"  📈 {abs(diff):,.0f} kr over avg"
                comparison_color = self.COLORS['accent_danger']
            
            comparison_label = ctk.CTkLabel(
                details_frame,
                text=comparison_text,
                font=ctk.CTkFont(size=12),
                text_color=comparison_color
            )
            comparison_label.pack(side="left", padx=(15, 0))
        
        # Location and condition
        location = item.get('location', 'Unknown')
        condition = item.get('condition', '')
        
        info_text = f"📍 {location}"
        if condition:
            info_text += f"  •  ✨ {condition}"
        
        info_label = ctk.CTkLabel(
            details_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        info_label.pack(side="right")
        
        # Bottom row: Actions
        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(5, 0))
        
        # Posted date
        posted = item.get('posted', '')
        if posted:
            posted_label = ctk.CTkLabel(
                actions_frame,
                text=f"📅 {posted}",
                font=ctk.CTkFont(size=11),
                text_color=self.COLORS['text_muted']
            )
            posted_label.pack(side="left")
        
        # View button
        url = item.get('url', '')
        if url:
            view_btn = ctk.CTkButton(
                actions_frame,
                text="🔗 View on FINN",
                width=120,
                height=30,
                font=ctk.CTkFont(size=11),
                fg_color=self.COLORS['accent_primary'],
                hover_color=self.COLORS['accent_secondary'],
                corner_radius=6,
                command=lambda u=url: webbrowser.open(u)
            )
            view_btn.pack(side="right")
            
    def _create_comparison_group(self, group_name: str, items: list):
        """Create a comparison group"""
        # Group header
        header_frame = ctk.CTkFrame(
            self.compare_scroll,
            fg_color=self.COLORS['bg_tertiary'],
            corner_radius=8
        )
        header_frame.pack(fill="x", pady=(15, 10), padx=5)
        
        header_label = ctk.CTkLabel(
            header_frame,
            text=f"⚖️ {group_name} ({len(items)} items)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text_primary']
        )
        header_label.pack(pady=10, padx=15, anchor="w")
        
        # Sort items by price
        items.sort(key=lambda x: x.get('price', float('inf')))
        
        # Create cards for each item
        for i, item in enumerate(items):
            is_best = i == 0 and item.get('price', 0) > 0
            self._create_comparison_card(item, is_best)
            
    def _create_comparison_card(self, item: dict, is_best: bool = False):
        """Create a comparison card"""
        border_color = self.COLORS['accent_success'] if is_best else self.COLORS['border']
        
        card = ctk.CTkFrame(
            self.compare_scroll,
            fg_color=self.COLORS['card_bg'],
            corner_radius=10,
            border_width=2 if is_best else 1,
            border_color=border_color
        )
        card.pack(fill="x", pady=4, padx=20)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=10)
        
        # Best deal badge
        if is_best:
            badge = ctk.CTkLabel(
                content,
                text="🏆 BEST PRICE",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=self.COLORS['accent_success']
            )
            badge.pack(anchor="w")
        
        # Title and price row
        row = ctk.CTkFrame(content, fg_color="transparent")
        row.pack(fill="x")
        
        title = item.get('title', 'Unknown')[:50]
        title_label = ctk.CTkLabel(
            row,
            text=title,
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_primary'],
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        price = item.get('price', 0)
        price_color = self.COLORS['accent_success'] if is_best else self.COLORS['text_primary']
        price_label = ctk.CTkLabel(
            row,
            text=f"{price:,.0f} kr",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=price_color
        )
        price_label.pack(side="right")
        
    def _get_score_color(self, score: int) -> str:
        """Get color based on deal score"""
        if score >= 90:
            return '#22c55e'  # Green
        elif score >= 80:
            return '#84cc16'  # Lime
        elif score >= 70:
            return '#eab308'  # Yellow
        elif score >= 60:
            return '#f97316'  # Orange
        else:
            return '#ef4444'  # Red
            
    def _search_complete(self):
        """Called when search is complete"""
        self.is_scraping = False
        self.search_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        
    def _stop_search(self):
        """Stop the current search"""
        self.is_scraping = False
        self.scraper.stop()
        self.progress_label.configure(text="⏹ Search stopped")
        self._search_complete()
        
    def _show_error(self, message: str):
        """Show error message"""
        self.progress_label.configure(text=f"❌ Error: {message}")
        messagebox.showerror("Search Error", message)
        
    def _export_results(self, format_type: str = 'csv'):
        """Export results to file"""
        if not self.current_results:
            messagebox.showinfo("Export", "No results to export. Run a search first!")
            return
            
        try:
            filepath = self.export_manager.export(
                self.current_results,
                format_type=format_type
            )
            self.status_label.configure(text=f"✅ Exported to {filepath}")
            messagebox.showinfo("Export Successful", f"Results exported to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            
    def _print_results(self):
        """Print results as HTML report"""
        if not self.current_results:
            messagebox.showinfo("Print", "No results to print. Run a search first!")
            return
            
        try:
            filepath = self.export_manager.create_print_report(
                self.current_results,
                search_params={
                    'keyword': self.search_entry.get(),
                    'category': self.category_var.get(),
                    'location': self.location_var.get()
                }
            )
            webbrowser.open(f'file://{filepath}')
            self.status_label.configure(text="✅ Print report opened in browser")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))


def main():
    """Main entry point"""
    app = FinnDealFinderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
