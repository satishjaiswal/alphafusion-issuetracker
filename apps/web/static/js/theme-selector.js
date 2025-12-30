/**
 * Enhanced Theme Selector System
 * Professional theme selector with search, categories, and favorites
 */

(function() {
    'use strict';

    const THEME_STORAGE_KEY = 'alphafusion-theme';
    const FAVORITES_STORAGE_KEY = 'alphafusion-theme-favorites';
    const RECENT_STORAGE_KEY = 'alphafusion-theme-recent';
    const DEFAULT_THEME = 'tradepro-dark';
    const MAX_RECENT = 5;
    
    const themes = [
        // Professional Dark Themes
        { id: 'tradepro-dark', name: 'TradePro Dark', icon: '📊', category: 'professional', colors: ['#0a0a0f', '#161b22', '#3b82f6', '#22c55e'] },
        { id: 'ms-office-dark', name: 'MS Office Dark', icon: '📄', category: 'professional', colors: ['#1f1f1f', '#2d2d30', '#0078d4', '#107c10'] },
        { id: 'vscode-dark', name: 'VS Code Dark', icon: '💻', category: 'professional', colors: ['#1e1e1e', '#252526', '#007acc', '#89d185'] },
        { id: 'github-dark', name: 'GitHub Dark', icon: '🐙', category: 'professional', colors: ['#0d1117', '#161b22', '#58a6ff', '#3fb950'] },
        { id: 'material-dark', name: 'Material Dark', icon: '🎨', category: 'professional', colors: ['#121212', '#1e1e1e', '#bb86fc', '#03dac6'] },
        
        // Professional Light Themes
        { id: 'light-professional', name: 'Light Professional', icon: '☀️', category: 'light', colors: ['#ffffff', '#f8f9fa', '#2563eb', '#16a34a'] },
        { id: 'ms-office-light', name: 'MS Office Light', icon: '📋', category: 'light', colors: ['#ffffff', '#f3f3f3', '#0078d4', '#107c10'] },
        { id: 'vscode-light', name: 'VS Code Light', icon: '💡', category: 'light', colors: ['#ffffff', '#f3f3f3', '#0078d4', '#107c10'] },
        { id: 'github-light', name: 'GitHub Light', icon: '☁️', category: 'light', colors: ['#ffffff', '#f6f8fa', '#0969da', '#1a7f37'] },
        { id: 'material-light', name: 'Material Light', icon: '🌞', category: 'light', colors: ['#fafafa', '#ffffff', '#6200ee', '#018786'] },
        
        // Colorful Themes
        { id: 'ocean-blue', name: 'Ocean Blue', icon: '🌊', category: 'colorful', colors: ['#0a1628', '#0f1e3a', '#0ea5e9', '#22d3ee'] },
        { id: 'forest-green', name: 'Forest Green', icon: '🌲', category: 'colorful', colors: ['#0a1a0f', '#0f2a1a', '#10b981', '#34d399'] },
        { id: 'sunset-orange', name: 'Sunset Orange', icon: '🌅', category: 'colorful', colors: ['#1a0a0a', '#2a1414', '#f97316', '#fb923c'] },
        { id: 'midnight-purple', name: 'Midnight Purple', icon: '🌙', category: 'colorful', colors: ['#0f0a1a', '#1a0f2a', '#a855f7', '#c084fc'] },
        { id: 'amber-gold', name: 'Amber Gold', icon: '✨', category: 'colorful', colors: ['#1a140a', '#2a1f0f', '#f59e0b', '#fbbf24'] },
        
        // Editor Themes
        { id: 'dracula', name: 'Dracula', icon: '🧛', category: 'editor', colors: ['#282a36', '#343746', '#bd93f9', '#50fa7b'] },
        { id: 'nord', name: 'Nord', icon: '❄️', category: 'editor', colors: ['#2e3440', '#3b4252', '#5e81ac', '#a3be8c'] },
        { id: 'one-dark', name: 'One Dark', icon: '🌑', category: 'editor', colors: ['#282c34', '#21252b', '#61afef', '#98c379'] },
        { id: 'monokai', name: 'Monokai', icon: '🎨', category: 'editor', colors: ['#272822', '#3e3d32', '#66d9ef', '#a6e22e'] },
        { id: 'solarized-dark', name: 'Solarized Dark', icon: '🌚', category: 'editor', colors: ['#002b36', '#073642', '#268bd2', '#859900'] },
        { id: 'solarized-light', name: 'Solarized Light', icon: '🌝', category: 'editor', colors: ['#fdf6e3', '#eee8d5', '#268bd2', '#859900'] },
        { id: 'gruvbox-dark', name: 'Gruvbox Dark', icon: '📦', category: 'editor', colors: ['#282828', '#3c3836', '#458588', '#98971a'] },
        { id: 'gruvbox-light', name: 'Gruvbox Light', icon: '📦', category: 'editor', colors: ['#fbf1c7', '#ebdbb2', '#458588', '#98971a'] },
        
        // Special Themes
        { id: 'cyberpunk', name: 'Cyberpunk', icon: '🤖', category: 'special', colors: ['#0a0a0f', '#161b22', '#00d9ff', '#00ff00'] },
        { id: 'carbon-gray', name: 'Carbon Gray', icon: '⚫', category: 'special', colors: ['#0a0a0a', '#1a1a1a', '#94a3b8', '#cbd5e1'] },
        { id: 'high-contrast-dark', name: 'High Contrast Dark', icon: '🔲', category: 'special', colors: ['#000000', '#1a1a1a', '#00a4ff', '#00ff00'] },
        { id: 'high-contrast-light', name: 'High Contrast Light', icon: '⬜', category: 'special', colors: ['#ffffff', '#f0f0f0', '#0066cc', '#008000'] }
    ];

    const categories = {
        'all': { name: 'All Themes', icon: '🎨' },
        'professional': { name: 'Professional', icon: '💼' },
        'light': { name: 'Light', icon: '☀️' },
        'colorful': { name: 'Colorful', icon: '🌈' },
        'editor': { name: 'Editor', icon: '📝' },
        'special': { name: 'Special', icon: '⭐' }
    };

    /**
     * Get current theme from localStorage or default
     */
    function getCurrentTheme() {
        const saved = localStorage.getItem(THEME_STORAGE_KEY);
        return saved && themes.find(t => t.id === saved) ? saved : DEFAULT_THEME;
    }

    /**
     * Get favorites from localStorage
     */
    function getFavorites() {
        try {
            const favs = localStorage.getItem(FAVORITES_STORAGE_KEY);
            return favs ? JSON.parse(favs) : [];
        } catch {
            return [];
        }
    }

    /**
     * Save favorites to localStorage
     */
    function saveFavorites(favs) {
        try {
            localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favs));
        } catch (e) {
            console.warn('Failed to save favorites', e);
        }
    }

    /**
     * Get recent themes from localStorage
     */
    function getRecent() {
        try {
            const recent = localStorage.getItem(RECENT_STORAGE_KEY);
            return recent ? JSON.parse(recent) : [];
        } catch {
            return [];
        }
    }

    /**
     * Save recent themes to localStorage
     */
    function saveRecent(recent) {
        try {
            localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
        } catch (e) {
            console.warn('Failed to save recent themes', e);
        }
    }

    /**
     * Add theme to recent
     */
    function addToRecent(themeId) {
        const recent = getRecent();
        const filtered = recent.filter(id => id !== themeId);
        filtered.unshift(themeId);
        saveRecent(filtered);
    }

    /**
     * Toggle favorite
     */
    function toggleFavorite(themeId) {
        const favs = getFavorites();
        const index = favs.indexOf(themeId);
        if (index > -1) {
            favs.splice(index, 1);
        } else {
            favs.push(themeId);
        }
        saveFavorites(favs);
        return favs.includes(themeId);
    }

    /**
     * Set theme on document
     */
    function setTheme(themeId) {
        const html = document.documentElement;
        html.setAttribute('data-theme', themeId);
        localStorage.setItem(THEME_STORAGE_KEY, themeId);
        addToRecent(themeId);
        
        // Emit custom event for components that need to react
        const event = new CustomEvent('themeChanged', { 
            detail: { theme: themeId } 
        });
        document.dispatchEvent(event);
    }

    /**
     * Get theme info by ID
     */
    function getThemeInfo(themeId) {
        return themes.find(t => t.id === themeId) || themes[0];
    }

    /**
     * Filter themes by search and category
     */
    function filterThemes(searchTerm = '', category = 'all') {
        return themes.filter(theme => {
            const matchesSearch = !searchTerm || 
                theme.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                theme.id.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesCategory = category === 'all' || theme.category === category;
            return matchesSearch && matchesCategory;
        });
    }

    /**
     * Create theme selector HTML
     */
    function createThemeSelectorHTML() {
        const currentTheme = getCurrentTheme();
        const currentThemeInfo = getThemeInfo(currentTheme);
        const favorites = getFavorites();
        const recent = getRecent();
        
        return `
            <div class="theme-selector">
                <button class="theme-selector-btn" id="theme-selector-btn" type="button" aria-label="Select theme">
                    <span class="theme-icon">${currentThemeInfo.icon}</span>
                    <span class="theme-name">${currentThemeInfo.name}</span>
                    <span class="theme-arrow">▼</span>
                </button>
                <div class="theme-dropdown" id="theme-dropdown" style="display: none;">
                    <div class="theme-dropdown-header">
                        <div class="theme-search-container">
                            <input type="text" 
                                   class="theme-search-input" 
                                   id="theme-search-input" 
                                   placeholder="Search themes..." 
                                   autocomplete="off">
                            <span class="theme-search-icon">🔍</span>
                        </div>
                        <div class="theme-category-tabs" id="theme-category-tabs">
                            ${Object.entries(categories).map(([id, cat]) => `
                                <button class="theme-category-tab ${id === 'all' ? 'active' : ''}" 
                                        data-category="${id}" 
                                        type="button">
                                    <span class="category-icon">${cat.icon}</span>
                                    <span class="category-name">${cat.name}</span>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                    <div class="theme-dropdown-body" id="theme-dropdown-body">
                        ${createThemeListHTML('all', '')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create theme list HTML
     */
    function createThemeListHTML(category = 'all', searchTerm = '') {
        const currentTheme = getCurrentTheme();
        const favorites = getFavorites();
        const recent = getRecent();
        const filtered = filterThemes(searchTerm, category);
        
        let html = '';
        
        // Favorites section
        const favoriteThemes = filtered.filter(t => favorites.includes(t.id));
        if (favoriteThemes.length > 0 && (category === 'all' || category === 'favorites')) {
            html += `
                <div class="theme-section">
                    <div class="theme-section-header">
                        <span class="theme-section-icon">⭐</span>
                        <span class="theme-section-title">Favorites</span>
                    </div>
                    <div class="theme-grid">
                        ${favoriteThemes.map(theme => createThemeCardHTML(theme, currentTheme, favorites)).join('')}
                    </div>
                </div>
            `;
        }
        
        // Recent section
        const recentThemes = filtered.filter(t => recent.includes(t.id) && !favorites.includes(t.id));
        if (recentThemes.length > 0 && (category === 'all' || category === 'recent')) {
            html += `
                <div class="theme-section">
                    <div class="theme-section-header">
                        <span class="theme-section-icon">🕒</span>
                        <span class="theme-section-title">Recent</span>
                    </div>
                    <div class="theme-grid">
                        ${recentThemes.map(theme => createThemeCardHTML(theme, currentTheme, favorites)).join('')}
                    </div>
                </div>
            `;
        }
        
        // Other themes
        const otherThemes = filtered.filter(t => !favorites.includes(t.id) && !recent.includes(t.id));
        if (otherThemes.length > 0) {
            html += `
                <div class="theme-section">
                    <div class="theme-section-header">
                        <span class="theme-section-icon">🎨</span>
                        <span class="theme-section-title">All Themes</span>
                        <span class="theme-section-count">${otherThemes.length}</span>
                    </div>
                    <div class="theme-grid">
                        ${otherThemes.map(theme => createThemeCardHTML(theme, currentTheme, favorites)).join('')}
                    </div>
                </div>
            `;
        }
        
        // Empty state
        if (filtered.length === 0) {
            html += `
                <div class="theme-empty-state">
                    <div class="theme-empty-icon">🔍</div>
                    <div class="theme-empty-title">No themes found</div>
                    <div class="theme-empty-description">Try a different search term or category</div>
                </div>
            `;
        }
        
        return html;
    }

    /**
     * Create theme card HTML
     */
    function createThemeCardHTML(theme, currentTheme, favorites) {
        const isActive = theme.id === currentTheme;
        const isFavorite = favorites.includes(theme.id);
        
        return `
            <div class="theme-card ${isActive ? 'active' : ''}" 
                 data-theme-id="${theme.id}"
                 data-theme-name="${theme.name}"
                 data-theme-category="${theme.category}">
                <div class="theme-card-header">
                    <span class="theme-card-icon">${theme.icon}</span>
                    <button class="theme-favorite-btn ${isFavorite ? 'active' : ''}" 
                            data-theme-id="${theme.id}"
                            type="button"
                            aria-label="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                        ${isFavorite ? '⭐' : '☆'}
                    </button>
                </div>
                <div class="theme-preview">
                    ${theme.colors.map(color => `
                        <span class="swatch" style="background: ${color}" title="${color}"></span>
                    `).join('')}
                </div>
                <div class="theme-card-footer">
                    <span class="theme-label">${theme.name}</span>
                    ${isActive ? '<span class="theme-check">✓</span>' : ''}
                </div>
            </div>
        `;
    }

    /**
     * Initialize theme selector
     */
    function initThemeSelector() {
        // Set initial theme immediately (before content renders to avoid flash)
        const currentTheme = getCurrentTheme();
        setTheme(currentTheme);

        // Setup UI when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupThemeSelector);
        } else {
            setTimeout(setupThemeSelector, 100);
        }
    }

    // Set theme immediately when script loads (synchronous execution in <head>)
    (function() {
        try {
            const saved = localStorage.getItem(THEME_STORAGE_KEY);
            const themeId = saved || DEFAULT_THEME;
            if (document.documentElement) {
                document.documentElement.setAttribute('data-theme', themeId);
            }
        } catch (e) {
            if (document.documentElement) {
                document.documentElement.setAttribute('data-theme', DEFAULT_THEME);
            }
        }
    })();

    /**
     * Setup theme selector UI and event listeners
     */
    function setupThemeSelector() {
        // Check if already initialized
        if (document.getElementById('theme-selector-btn')) {
            return;
        }
        
        // Find where to insert theme selector
        const navActions = document.querySelector('.nav-actions');
        if (!navActions) {
            setTimeout(setupThemeSelector, 200);
            return;
        }

        // Insert theme selector
        const lastUpdated = navActions.querySelector('#last-updated');
        if (lastUpdated) {
            lastUpdated.insertAdjacentHTML('beforebegin', createThemeSelectorHTML());
        } else {
            navActions.insertAdjacentHTML('beforeend', createThemeSelectorHTML());
        }

        // Setup event listeners
        const themeBtn = document.getElementById('theme-selector-btn');
        const themeDropdown = document.getElementById('theme-dropdown');
        const searchInput = document.getElementById('theme-search-input');
        const categoryTabs = document.querySelectorAll('.theme-category-tab');

        if (!themeBtn || !themeDropdown) {
            return;
        }

        let currentCategory = 'all';
        let currentSearch = '';

        // Toggle dropdown
        themeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = themeDropdown.style.display !== 'none';
            themeDropdown.style.display = isOpen ? 'none' : 'block';
            if (!isOpen && searchInput) {
                setTimeout(() => searchInput.focus(), 100);
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!themeDropdown.contains(e.target) && !themeBtn.contains(e.target)) {
                themeDropdown.style.display = 'none';
            }
        });

        // Search functionality
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                currentSearch = e.target.value;
                searchTimeout = setTimeout(() => {
                    updateThemeList(currentCategory, currentSearch);
                }, 150);
            });
        }

        // Category tabs
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                currentCategory = tab.getAttribute('data-category');
                categoryTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                updateThemeList(currentCategory, currentSearch);
            });
        });

        // Delegate event listeners for dynamic content
        themeDropdown.addEventListener('click', (e) => {
            // Theme card click
            const themeCard = e.target.closest('.theme-card');
            if (themeCard) {
                const themeId = themeCard.getAttribute('data-theme-id');
                if (themeId) {
                    switchTheme(themeId);
                    return;
                }
            }

            // Favorite button click
            const favoriteBtn = e.target.closest('.theme-favorite-btn');
            if (favoriteBtn) {
                e.stopPropagation();
                const themeId = favoriteBtn.getAttribute('data-theme-id');
                const isFavorite = toggleFavorite(themeId);
                favoriteBtn.textContent = isFavorite ? '⭐' : '☆';
                favoriteBtn.classList.toggle('active', isFavorite);
                updateThemeList(currentCategory, currentSearch);
            }
        });
    }

    /**
     * Update theme list
     */
    function updateThemeList(category = 'all', searchTerm = '') {
        const body = document.getElementById('theme-dropdown-body');
        if (body) {
            body.innerHTML = createThemeListHTML(category, searchTerm);
        }
    }

    /**
     * Switch to a new theme
     */
    function switchTheme(themeId) {
        if (!themes.find(t => t.id === themeId)) {
            console.warn(`Theme ${themeId} not found`);
            return;
        }

        setTheme(themeId);
        updateThemeSelectorUI(themeId);
        
        // Update theme list to reflect changes
        const searchInput = document.getElementById('theme-search-input');
        const activeTab = document.querySelector('.theme-category-tab.active');
        const category = activeTab ? activeTab.getAttribute('data-category') : 'all';
        const searchTerm = searchInput ? searchInput.value : '';
        updateThemeList(category, searchTerm);
        
        // Close dropdown
        const themeDropdown = document.getElementById('theme-dropdown');
        if (themeDropdown) {
            themeDropdown.style.display = 'none';
        }
    }

    /**
     * Update theme selector UI to reflect current theme
     */
    function updateThemeSelectorUI(themeId) {
        const themeInfo = getThemeInfo(themeId);
        const themeBtn = document.getElementById('theme-selector-btn');
        const themeName = themeBtn?.querySelector('.theme-name');
        const themeIcon = themeBtn?.querySelector('.theme-icon');

        if (themeName) themeName.textContent = themeInfo.name;
        if (themeIcon) themeIcon.textContent = themeInfo.icon;
    }

    // Initialize on load
    initThemeSelector();

    // Export for global access
    window.ThemeSelector = {
        switchTheme,
        getCurrentTheme,
        getThemeInfo,
        themes,
        getFavorites,
        toggleFavorite
    };

})();
