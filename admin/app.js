/**
 * Petrosia Admin Interface
 * Matches index.html structure
 */

const API_BASE_URL = window.PETROSIA_API_URL || window.location.origin;

// State
let currentView = 'articles';
let currentArticle = null;
let articles = [];
let editorContent = {}; // Store content for each language tab

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupEditorTabs();
    loadArticles();
});

// Navigation
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);

            // Update active state
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchView(view) {
    currentView = view;

    // Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));

    // Show selected view
    const viewElement = document.getElementById(`${view}-view`);
    if (viewElement) {
        viewElement.classList.remove('hidden');
    }

    // Load data for view
    if (view === 'articles') {
        loadArticles();
    } else if (view === 'analytics') {
        loadAnalytics();
    }
}

// Editor tabs
function setupEditorTabs() {
    const tabs = document.querySelectorAll('.editor-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const lang = tab.dataset.lang;
            switchEditorTab(lang);
        });
    });
}

function switchEditorTab(lang) {
    // Save current content before switching
    const currentTab = document.querySelector('.editor-tab.active');
    if (currentTab) {
        const currentLang = currentTab.dataset.lang;
        editorContent[currentLang] = {
            title: document.getElementById('editor-title-input').value,
            body: document.getElementById('editor-body').value
        };
    }

    // Update tab UI
    document.querySelectorAll('.editor-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.lang === lang);
    });

    // Load content for selected language
    const content = editorContent[lang] || { title: '', body: '' };
    document.getElementById('editor-title-input').value = content.title;
    document.getElementById('editor-body').value = content.body;
}

// Called by onclick in HTML
function showEditor(article = null) {
    currentArticle = article;
    editorContent = {};

    if (article) {
        // Editing existing article
        document.getElementById('editor-title').textContent = 'Edit Article';
        document.getElementById('editor-slug').value = article.slug;
        document.getElementById('editor-slug').disabled = true;

        // Load content for each language
        for (const [lang, content] of Object.entries(article.content || {})) {
            editorContent[lang] = {
                title: content.title || '',
                body: content.body || ''
            };
        }
    } else {
        // New article
        document.getElementById('editor-title').textContent = 'New Article';
        document.getElementById('editor-slug').value = '';
        document.getElementById('editor-slug').disabled = false;
    }

    // Switch to English tab and load its content
    switchEditorTab('en');

    // Show editor view
    document.getElementById('articles-view').classList.add('hidden');
    document.getElementById('editor-view').classList.remove('hidden');
}

function closeEditor() {
    document.getElementById('editor-view').classList.add('hidden');
    document.getElementById('articles-view').classList.remove('hidden');
    document.getElementById('save-status').textContent = '';
}

// Articles
async function loadArticles() {
    const status = document.getElementById('filter-status').value;
    const language = document.getElementById('filter-language').value;

    const listContainer = document.getElementById('articles-list');
    listContainer.innerHTML = '<div class="loading">Loading articles...</div>';

    try {
        let url = `${API_BASE_URL}/api/articles?`;
        if (status) url += `status=${status}&`;
        if (language) url += `language=${language}&`;

        const response = await fetch(url);
        articles = await response.json();

        renderArticles(articles);
    } catch (error) {
        console.error('Error loading articles:', error);
        listContainer.innerHTML = '<div class="loading">Error loading articles</div>';
    }
}

function renderArticles(articlesToRender) {
    const listContainer = document.getElementById('articles-list');

    if (articlesToRender.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>No articles found</p>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = '';

    articlesToRender.forEach(article => {
        const card = createArticleCard(article);
        listContainer.appendChild(card);
    });
}

function createArticleCard(article) {
    const card = document.createElement('div');
    card.className = 'article-card';

    const languages = Object.keys(article.content || {});
    const primaryLang = languages.includes('en') ? 'en' : languages[0];
    const title = article.content[primaryLang]?.title || article.slug;

    const updatedAt = article.updated_at
        ? new Date(article.updated_at).toLocaleDateString()
        : 'N/A';

    card.innerHTML = `
        <h3>${escapeHtml(title)}</h3>
        <div class="article-card-meta">
            <span>slug: ${escapeHtml(article.slug)}</span>
            <span>status: ${article.status}</span>
            <span>updated: ${updatedAt}</span>
        </div>
        <div class="article-languages">
            ${languages.map(lang => `<span class="lang-badge">${lang}</span>`).join('')}
        </div>
    `;

    card.addEventListener('click', () => showEditor(article));

    return card;
}

async function saveArticle() {
    const slug = document.getElementById('editor-slug').value.trim();
    const statusEl = document.getElementById('save-status');

    if (!slug) {
        statusEl.textContent = 'Slug is required';
        statusEl.style.color = '#e74c3c';
        return;
    }

    // Save current tab content before saving
    const currentTab = document.querySelector('.editor-tab.active');
    if (currentTab) {
        const currentLang = currentTab.dataset.lang;
        editorContent[currentLang] = {
            title: document.getElementById('editor-title-input').value,
            body: document.getElementById('editor-body').value
        };
    }

    // Filter out empty content
    const content = {};
    for (const [lang, data] of Object.entries(editorContent)) {
        if (data.title || data.body) {
            content[lang] = {
                title: data.title || '',
                body: data.body || ''
            };
        }
    }

    if (Object.keys(content).length === 0) {
        statusEl.textContent = 'At least one language content is required';
        statusEl.style.color = '#e74c3c';
        return;
    }

    statusEl.textContent = 'Saving...';
    statusEl.style.color = '#86868b';

    try {
        if (currentArticle) {
            // Update existing - use the single-call update endpoint for each language
            // Backend endpoint: PUT /api/articles/{slug}/{language}
            for (const [lang, data] of Object.entries(content)) {
                const response = await fetch(`${API_BASE_URL}/api/articles/${slug}/${lang}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: data.title,
                        body: data.body
                    })
                });

                if (!response.ok) {
                    throw new Error(`Failed to update ${lang} content`);
                }
            }
            statusEl.textContent = 'Saved!';
            statusEl.style.color = '#27ae60';
        } else {
            // Create new article
            const response = await fetch(`${API_BASE_URL}/api/articles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    slug: slug,
                    content: content,
                    status: 'published'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create article');
            }

            statusEl.textContent = 'Created!';
            statusEl.style.color = '#27ae60';

            // Switch to edit mode
            const newArticle = await response.json();
            currentArticle = newArticle;
            document.getElementById('editor-slug').disabled = true;
            document.getElementById('editor-title').textContent = 'Edit Article';
        }

        // Refresh article list
        loadArticles();

    } catch (error) {
        console.error('Error saving article:', error);
        statusEl.textContent = error.message || 'Error saving';
        statusEl.style.color = '#e74c3c';
    }
}

// Search Test
async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return;

    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '<div class="loading">Searching...</div>';

    try {
        // Backend uses GET /api/search with query params
        const params = new URLSearchParams({
            q: query,
            language: 'en',
            limit: 5
        });
        const response = await fetch(`${API_BASE_URL}/api/search?${params}`);

        const results = await response.json();
        renderSearchResults(results || []);
    } catch (error) {
        console.error('Error searching:', error);
        resultsContainer.innerHTML = '<div class="loading">Error performing search</div>';
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');

    if (results.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
        return;
    }

    container.innerHTML = '';

    results.forEach(result => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'search-result-item';
        resultDiv.innerHTML = `
            <div class="search-result-title">${escapeHtml(result.title)}</div>
            <span class="search-result-score">${(result.score * 100).toFixed(1)}% match</span>
            <div class="search-result-body">${escapeHtml(result.body?.substring(0, 300) || '')}...</div>
        `;
        container.appendChild(resultDiv);
    });
}

// Analytics
async function loadAnalytics() {
    // Load article count
    try {
        const articlesResponse = await fetch(`${API_BASE_URL}/api/articles`);
        const articlesData = await articlesResponse.json();
        document.getElementById('stat-articles').textContent = articlesData.length;

        // Count unique languages
        const languages = new Set();
        articlesData.forEach(article => {
            Object.keys(article.content || {}).forEach(lang => languages.add(lang));
        });
        document.getElementById('stat-languages').textContent = languages.size;
    } catch (error) {
        console.error('Error loading article stats:', error);
    }

    // Load recent questions
    loadRecentQuestions();
}

async function loadRecentQuestions() {
    const container = document.getElementById('recent-questions-list');
    container.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/history?limit=20`);
        const questions = await response.json();

        document.getElementById('stat-questions').textContent = questions.length;

        if (questions.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No questions yet</p></div>';
            return;
        }

        container.innerHTML = '';

        questions.forEach(q => {
            const item = document.createElement('div');
            item.className = 'question-item';
            item.innerHTML = `
                <div class="question-text">${escapeHtml(q.query)}</div>
                <div class="question-meta">
                    ${q.provider} - ${new Date(q.created_at).toLocaleString()}
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading questions:', error);
        container.innerHTML = '<div class="loading">Error loading questions</div>';
    }
}

// Utility
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
