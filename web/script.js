// Загрузка данных
let articlesData = [];               # Массив для хранения статей
let videosData = [];                 # Массив для хранения видео
let userStats = null;                # Объект со статистикой пользователя
let userTelegramId = null;           # Telegram ID текущего пользователя

# Получаем Telegram ID из URL (можно передавать через параметр)
function getTelegramIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('user_id');
}

# Загрузка статей из локального файла
async function loadArticles() {
    try {
        const response = await fetch('articles/data.json');
        if (!response.ok) {
            throw new Error('Ошибка загрузки');
        }
        const data = await response.json();
        articlesData = data.articles || [];
        renderArticles(articlesData);
    } catch (error) {
        console.error('Ошибка загрузки статей:', error);
        document.getElementById('articles-container').innerHTML =
            '<div class="error">❌ Не удалось загрузить статьи</div>';
    }
}

# Загрузка видео из локального файла
async function loadVideos() {
    try {
        const response = await fetch('articles/data.json');
        if (!response.ok) {
            throw new Error('Ошибка загрузки');
        }
        const data = await response.json();
        videosData = data.videos || [];
        renderVideos(videosData);
    } catch (error) {
        console.error('Ошибка загрузки видео:', error);
        document.getElementById('videos-container').innerHTML =
            '<div class="error">❌ Не удалось загрузить видео</div>';
    }
}

# Отрисовка статистики (используем данные из URL или заглушку)
function renderStats() {
    const container = document.getElementById('stats-container');

    # Пытаемся получить ID пользователя
    const telegramId = getTelegramIdFromUrl();

    if (!telegramId) {
        # Если нет ID, показываем заглушку
        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-emoji">📝</div>
                <div class="stat-label">Всего записей</div>
                <div class="stat-value">0</div>
                <div class="stat-total">🔥 Серия: 0 дней</div>
            </div>
            <div class="stat-card">
                <div class="stat-emoji">😊</div>
                <div class="stat-label">Настроение</div>
                <div class="stat-value">0/10</div>
            </div>
            <div class="stat-card">
                <div class="stat-emoji">⚡</div>
                <div class="stat-label">Энергия</div>
                <div class="stat-value">0/10</div>
            </div>
            <div class="stat-card">
                <div class="stat-emoji">😰</div>
                <div class="stat-label">Тревожность</div>
                <div class="stat-value">0/10</div>
            </div>
            <div class="stat-card">
                <div class="stat-emoji">😴</div>
                <div class="stat-label">Сон</div>
                <div class="stat-value">0 ч</div>
            </div>
        `;
        return;
    }

    # Здесь будет запрос к вашему будущему API
    # Пока показываем заглушку с пояснением
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-emoji">📝</div>
            <div class="stat-label">Всего записей</div>
            <div class="stat-value">?</div>
            <div class="stat-total">🔥 Серия: ? дней</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😊</div>
            <div class="stat-label">Настроение</div>
            <div class="stat-value">?/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">⚡</div>
            <div class="stat-label">Энергия</div>
            <div class="stat-value">?/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😰</div>
            <div class="stat-label">Тревожность</div>
            <div class="stat-value">?/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😴</div>
            <div class="stat-label">Сон</div>
            <div class="stat-value">? ч</div>
        </div>
    `;
}

# Отрисовка статей на странице
function renderArticles(articles) {
    const container = document.getElementById('articles-container');

    if (!articles || articles.length === 0) {
        container.innerHTML = '<div class="loading">Нет статей</div>';
        return;
    }

    container.innerHTML = articles.map(article => `
        <div class="article-card" data-category="${article.category || 'все'}">
            <div class="article-image" style="background-image: url('${article.image || 'https://via.placeholder.com/300x200'}')"></div>
            <div class="article-content">
                <span class="article-tag">${article.tag || 'статья'}</span>
                <h3 class="article-title">${article.title}</h3>
                <p class="article-excerpt">${article.excerpt || ''}</p>
                <a href="#" class="article-link" onclick="openArticle(${article.id})">
                    Читать статью <span>→</span>
                </a>
            </div>
        </div>
    `).join('');
}

# Отрисовка видео на странице
function renderVideos(videos) {
    const container = document.getElementById('videos-container');

    if (!videos || videos.length === 0) {
        container.innerHTML = '<div class="loading">Нет видео</div>';
        return;
    }

    container.innerHTML = videos.map(video => `
        <div class="video-card" data-category="${video.category || 'все'}">
            <div class="video-thumbnail" style="background-image: url('${video.thumbnail || 'https://via.placeholder.com/300x180'}')"
                 onclick="openVideo('${video.youtubeId || ''}')">
                <div class="play-button">▶</div>
            </div>
            <div class="video-info">
                <h3 class="video-title">${video.title}</h3>
                <div class="video-channel">${video.channel || 'Канал'} • ${video.duration || '00:00'}</div>
                <div class="video-tags">
                    ${(video.tags || []).map(tag => `<span class="video-tag">${tag}</span>`).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

# Фильтрация статей по категории
function filterArticles(category) {
    if (!articlesData || articlesData.length === 0) return;

    if (category === 'all') {
        renderArticles(articlesData);
    } else {
        const filtered = articlesData.filter(a => (a.category || '').toLowerCase() === category);
        renderArticles(filtered);
    }
}

# Фильтрация видео по категории
function filterVideos(category) {
    if (!videosData || videosData.length === 0) return;

    if (category === 'all') {
        renderVideos(videosData);
    } else {
        const filtered = videosData.filter(v => (v.category || '').toLowerCase() === category);
        renderVideos(filtered);
    }
}

# Открыть статью (пока только заглушка)
function openArticle(id) {
    const article = articlesData.find(a => a.id === id);
    if (article) {
        alert('📖 Полная версия статьи будет доступна в следующем обновлении');
    }
}

# Открыть видео в модальном окне
function openVideo(youtubeId) {
    if (!youtubeId) {
        alert('🎥 Видео временно недоступно');
        return;
    }

    const modal = document.getElementById('videoModal');
    const iframe = document.getElementById('videoIframe');
    iframe.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1`;
    modal.classList.add('active');
}

# Закрыть модальное окно с видео
function closeModal() {
    const modal = document.getElementById('videoModal');
    const iframe = document.getElementById('videoIframe');
    iframe.src = '';
    modal.classList.remove('active');
}

# Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    # Показываем статистику
    renderStats();

    # Загружаем статьи и видео
    loadArticles();
    loadVideos();

    # Фильтры для статей
    document.querySelectorAll('[data-filter]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            filterArticles(e.target.dataset.filter);
        });
    });

    # Фильтры для видео
    document.querySelectorAll('[data-filter-video]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-filter-video]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            filterVideos(e.target.dataset.filterVideo);
        });
    });

    # Закрытие модального окна по крестику
    const modalClose = document.querySelector('.modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }

    # Закрытие модального окна по клику вне его
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
});

# Добавляем модальное окно для видео, если его нет на странице
if (!document.getElementById('videoModal')) {
    document.body.insertAdjacentHTML('beforeend', `
        <div class="modal" id="videoModal">
            <span class="modal-close">&times;</span>
            <div class="modal-content">
                <div class="video-wrapper">
                    <iframe id="videoIframe" src="" frameborder="0" allowfullscreen></iframe>
                </div>
            </div>
        </div>
    `);
}