// Загрузка данных
let articlesData = [];
let videosData = [];

// Загрузка статистики пользователя (будет получать от бота)
async function loadUserStats() {
    // Здесь будет запрос к API бота
    // Пока заглушка
    const stats = {
        totalEntries: 42,
        avgMood: 7.8,
        avgEnergy: 6.5,
        avgAnxiety: 4.2,
        avgSleep: 7.5,
        streak: 5
    };

    renderStats(stats);
}

// Загрузка статей
async function loadArticles() {
    try {
        const response = await fetch('articles/data.json');
        const data = await response.json();
        articlesData = data.articles;
        renderArticles(articlesData);
    } catch (error) {
        console.error('Ошибка загрузки статей:', error);
        document.getElementById('articles-container').innerHTML =
            '<div class="error">Ошибка загрузки статей</div>';
    }
}

// Загрузка видео
async function loadVideos() {
    try {
        const response = await fetch('articles/data.json');
        const data = await response.json();
        videosData = data.videos;
        renderVideos(videosData);
    } catch (error) {
        console.error('Ошибка загрузки видео:', error);
        document.getElementById('videos-container').innerHTML =
            '<div class="error">Ошибка загрузки видео</div>';
    }
}

// Отрисовка статистики
function renderStats(stats) {
    const container = document.getElementById('stats-container');

    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-emoji">📝</div>
            <div class="stat-label">Всего записей</div>
            <div class="stat-value">${stats.totalEntries}</div>
            <div class="stat-total">🔥 Серия: ${stats.streak} дней</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😊</div>
            <div class="stat-label">Настроение</div>
            <div class="stat-value">${stats.avgMood}/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">⚡</div>
            <div class="stat-label">Энергия</div>
            <div class="stat-value">${stats.avgEnergy}/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😰</div>
            <div class="stat-label">Тревожность</div>
            <div class="stat-value">${stats.avgAnxiety}/10</div>
        </div>
        <div class="stat-card">
            <div class="stat-emoji">😴</div>
            <div class="stat-label">Сон</div>
            <div class="stat-value">${stats.avgSleep} ч</div>
        </div>
    `;
}

// Отрисовка статей
function renderArticles(articles) {
    const container = document.getElementById('articles-container');

    if (articles.length === 0) {
        container.innerHTML = '<div class="loading">Нет статей</div>';
        return;
    }

    container.innerHTML = articles.map(article => `
        <div class="article-card" data-category="${article.category}">
            <div class="article-image" style="background-image: url('${article.image}')"></div>
            <div class="article-content">
                <span class="article-tag">${article.tag}</span>
                <h3 class="article-title">${article.title}</h3>
                <p class="article-excerpt">${article.excerpt}</p>
                <a href="#" class="article-link" onclick="openArticle(${article.id})">
                    Читать статью <span>→</span>
                </a>
            </div>
        </div>
    `).join('');
}

// Отрисовка видео
function renderVideos(videos) {
    const container = document.getElementById('videos-container');

    if (videos.length === 0) {
        container.innerHTML = '<div class="loading">Нет видео</div>';
        return;
    }

    container.innerHTML = videos.map(video => `
        <div class="video-card" data-category="${video.category}">
            <div class="video-thumbnail" style="background-image: url('${video.thumbnail}')"
                 onclick="openVideo('${video.youtubeId}')">
                <div class="play-button">▶</div>
            </div>
            <div class="video-info">
                <h3 class="video-title">${video.title}</h3>
                <div class="video-channel">${video.channel} • ${video.duration}</div>
                <div class="video-tags">
                    ${video.tags.map(tag => `<span class="video-tag">${tag}</span>`).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

// Фильтрация статей
function filterArticles(category) {
    if (category === 'all') {
        renderArticles(articlesData);
    } else {
        const filtered = articlesData.filter(a => a.category === category);
        renderArticles(filtered);
    }
}

// Фильтрация видео
function filterVideos(category) {
    if (category === 'all') {
        renderVideos(videosData);
    } else {
        const filtered = videosData.filter(v => v.category === category);
        renderVideos(filtered);
    }
}

// Открыть статью
function openArticle(id) {
    // Здесь будет открытие модального окна со статьей
    console.log('Открыть статью', id);
}

// Открыть видео
function openVideo(youtubeId) {
    const modal = document.getElementById('videoModal');
    const iframe = document.getElementById('videoIframe');
    iframe.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1`;
    modal.classList.add('active');
}

// Закрыть модальное окно
function closeModal() {
    const modal = document.getElementById('videoModal');
    const iframe = document.getElementById('videoIframe');
    iframe.src = '';
    modal.classList.remove('active');
}

// Инициализация фильтров
document.addEventListener('DOMContentLoaded', () => {
    loadUserStats();
    loadArticles();
    loadVideos();

    // Фильтры для статей
    document.querySelectorAll('[data-filter]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            filterArticles(e.target.dataset.filter);
        });
    });

    // Фильтры для видео
    document.querySelectorAll('[data-filter-video]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-filter-video]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            filterVideos(e.target.dataset.filterVideo);
        });
    });

    // Закрытие модального окна
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
});

// Добавляем модальное окно для видео
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