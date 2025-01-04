import streamlit as st
from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo
from typing import List, Optional
import instaloader
import re
import time
import itertools

# -----------------------------
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ИЗ INSTAGRAM
# -----------------------------
def extract_username(url: str) -> str:
    """Извлекает имя пользователя из ссылки на Instagram-профиль."""
    match = re.search(r'instagram\.com/([^/?#&]+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Невозможно извлечь имя пользователя из ссылки.")

def parse_instagram_profile(url: str, num_posts: int = 3):
    """
    Парсинг профиля Instagram с обработкой ошибок и ретраями
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            username = extract_username(url)
            L = instaloader.Instaloader()
            
            # Добавляем задержку между запросами
            time.sleep(2)
            
            profile = instaloader.Profile.from_username(L.context, username)
            
            return {
                "username": username,
                "profile_pic_url": profile.profile_pic_url,
                "bio": profile.biography,
                "captions": [
                    post.caption if post.caption else "Подпись отсутствует"
                    for post in itertools.islice(profile.get_posts(), num_posts)
                ]
            }
        except instaloader.exceptions.InstaloaderException as e:
            retry_count += 1
            if retry_count == max_retries:
                raise Exception(f"Ошибка при парсинге профиля после {max_retries} попыток: {str(e)}")
            time.sleep(5)  # Ждем перед повторной попыткой

# -----------------------------
# ИНИЦИАЛИЗАЦИЯ АГЕНТОВ
# -----------------------------
def initialize_agents(api_key: str) -> tuple[Optional[Agent], Optional[Agent], Optional[Agent]]:
    if not api_key or len(api_key.strip()) < 10:  # Простая валидация ключа
        st.error("Некорректный API ключ")
        return None, None, None
        
    try:
        model = Gemini(id="gemini-2.0-flash-exp", api_key=api_key)

        # Агент: «Арт-директор»
        art_director_agent = Agent(
            model=model,
            instructions=[
                "Ты — профессиональный арт-директор, оценивающий визуальную составляющую Instagram-профиля.",
                "1. Анализируй композицию, свет, цвета и общее впечатление от фото.",
                "2. Давай советы по улучшению визуального ряда в профессиональной форме.",
                "3. Замечай детали, которые бросаются в глаза и могут повысить/снизить интерес к профилю.",
                "Будь при этом полезным и конкретным."
            ],
            markdown=True
        )

        # Агент: «Копирайтинг и Сторителлинг»
        copy_agent = Agent(
            model=model,
            instructions=[
                "Ты — эксперт по копирайтингу и сторителлингу, анализируешь тексты постов в Instagram.",
                "1. Обращай внимание на стиль изложения, цепляющие фразы, форматирование.",
                "2. Давай рекомендации, как усилить вовлечённость и повысить интерес.",
                "3. Можно использовать легкий юмор или иронию для придания оттенка 'прожарки'."
            ],
            markdown=True
        )

        # Агент: «Маркетолог/Конкурентный исследователь»
        market_agent = Agent(
            model=model,
            tools=[DuckDuckGo(search=True)],
            instructions=[
                "Ты — маркетолог, занимаешься конкурентным анализом и позиционированием профиля в Instagram.",
                "1. Исходя из описания профиля (bio) и общего направления, давай оценку и 'прожарку'.",
                "2. Подмечай, как профиль может выглядеть на фоне конкурентов.",
                "3. Да, ирония и юмор уместны, но не забывай о реальных советах по улучшению.",
                "4. Найди и проанализируй топ-5 популярных Instagram-блогеров из той же ниши:",
                "   - Используй DuckDuckGo для поиска лидеров в этом сегменте",
                "   - Сравни стиль, подачу и особенности их контента",
                "   - Укажи ссылки на их профили как референсы",
                "   - Выдели фишки, которые можно адаптировать",
                "Представь, что даёшь совет человеку, который хочет выделиться на рынке, опираясь на лучшие практики в нише."
            ],
            markdown=True
        )

        return art_director_agent, copy_agent, market_agent
    except Exception as e:
        st.error(f"Ошибка инициализации Gemini: {str(e)}")
        return None, None, None

# -----------------------------
# САЙДБАР ДЛЯ API-КЛЮЧА
# -----------------------------
with st.sidebar:
    st.header("🔑 API Configuration")

    if "api_key_input" not in st.session_state:
        st.session_state.api_key_input = ""
        
    api_key = st.text_input(
        "Enter your Gemini API Key",
        value=st.session_state.api_key_input,
        type="password",
        help="Get your API key from Google AI Studio",
        key="api_key_widget"
    )

    if api_key != st.session_state.api_key_input:
        st.session_state.api_key_input = api_key
    
    if api_key:
        st.success("API Key provided! ✅")
    else:
        st.warning("Please enter your API key to proceed")
        st.markdown("""
        To get your API key:
        1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
        """)

# -----------------------------
# ОСНОВНОЙ ИНТЕРФЕЙС
# -----------------------------
st.title("Мультиагентный анализ Instagram-профиля")

if st.session_state.api_key_input:
    # Инициализация агентов
    art_director_agent, copy_agent, market_agent = initialize_agents(st.session_state.api_key_input)
    
    if all([art_director_agent, copy_agent, market_agent]):
        
        # -----------------------------
        # Блок для ввода ссылки на IG-профиль
        # -----------------------------
        st.header("🔗 Введите ссылку на Instagram-профиль")
        profile_url = st.text_input(
            "Например: https://www.instagram.com/instagram/",
            placeholder="Введите ссылку..."
        )

        # -----------------------------
        # Блок конфигурации анализа
        # -----------------------------
        st.header("🎯 Конфигурация анализа")

        analysis_types = st.multiselect(
            "Выберите тип анализа",
            ["Арт-директорский обзор", "Копирайтинг/Сторителлинг", "Маркетинг/Конкурентный анализ"],
            default=["Арт-директорский обзор"]
        )

        specific_elements = st.multiselect(
            "На чём сфокусироваться?",
            [
                "Композиция, цвет", 
                "Стиль и подача в тексте", 
                "Юмор и ирония", 
                "Конкурентное позиционирование"
            ]
        )

        context = st.text_area(
            "Дополнительный контекст",
            placeholder="Опишите, для чего нужна эта 'прожарка': цель, аудитория и т.д."
        )

        # -----------------------------
        # Кнопка запуска анализа
        # -----------------------------
        if st.button("🚀 Run Analysis", type="primary"):
            if profile_url:
                try:
                    # Пытаемся спарсить данные с профиля
                    with st.spinner("Парсим профиль..."):
                        data = parse_instagram_profile(profile_url, num_posts=3)

                    if data:
                        st.header("📊 Результаты анализа")

                        # Собираем данные для агентов
                        username = data["username"]
                        profile_pic_url = data["profile_pic_url"]
                        bio = data["bio"]
                        captions = data["captions"]

                        all_images = [profile_pic_url] if profile_pic_url else []

                        # --- Арт-директорский обзор ---
                        if "Арт-директорский обзор" in analysis_types:
                            with st.spinner("🎨 Анализ фото профиля арт-директором..."):
                                prompt_art = f"""
                                Проанализируй визуальную часть фото профиля.
                                Учти следующие моменты: {', '.join(specific_elements)}.
                                Доп. контекст: {context}
                                Дай рекомендации в стиле 'прожарки', но с пользой.
                                """
                                response_art = art_director_agent.run(
                                    message=prompt_art,
                                    images=all_images  # Если модель поддерживает URL
                                )
                                st.subheader("🎨 Арт-директорский обзор")
                                st.markdown(response_art.content)

                        # --- Копирайтинг и сторителлинг ---
                        if "Копирайтинг/Сторителлинг" in analysis_types:
                            with st.spinner("✍️ Анализ подписей постов..."):
                                posts_text = "\n\n".join([f"Пост #{i+1}:\n{c}" for i, c in enumerate(captions)])
                                prompt_copy = f"""
                                Ниже тексты последних постов Instagram-профиля:
                                {posts_text}

                                Анализируй, учитывая такие моменты: {', '.join(specific_elements)}.
                                Доп. контекст: {context}

                                Дай комментарии и советы по улучшению сторителлинга и вовлечения,
                                можно с долей юмора.
                                """
                                response_copy = copy_agent.run(message=prompt_copy)
                                st.subheader("✍️ Копирайтинг/Сторителлинг")
                                st.markdown(response_copy.content)

                        # --- Маркетинг и конкурентный анализ ---
                        if "Маркетинг/Конкурентный анализ" in analysis_types:
                            with st.spinner("📊 Маркетинговая 'прожарка'..."):
                                prompt_market = f"""
                                Вот описание профиля (bio):
                                '{bio}'

                                Учти следующие моменты: {', '.join(specific_elements)}.
                                Доп. контекст: {context}

                                Дай анализ позиционирования и конкурентной уникальности,
                                можно с ноткой иронии, но с реальными советами по улучшению.
                                """
                                response_market = market_agent.run(message=prompt_market)
                                st.subheader("📊 Маркетинг/Конкурентный анализ")
                                st.markdown(response_market.content)

                        # Если выбрано несколько типов анализа, выведем дополнительный блок
                        if len(analysis_types) > 1:
                            st.subheader("🎯 Основные выводы")
                            st.info("""
                            Обратите внимание на разные аспекты:
                            - Арт-директорский обзор: визуальное оформление и уникальный стиль
                            - Копирайтинг/Сторителлинг: тексты постов и взаимодействие с аудиторией
                            - Маркетинг/Конкурентный анализ: рыночная ценность и позиционирование
                            """)

                    else:
                        st.warning("Не удалось получить данные об этом профиле.")
                except Exception as e:
                    st.error(f"Произошла ошибка при анализе профиля: {str(e)}")
            else:
                st.warning("Пожалуйста, введите ссылку на профиль для анализа.")
    else:
        st.info("👈 Пожалуйста, введите API-ключ в боковой панели, чтобы начать.")
else:
    st.info("👈 Пожалуйста, введите API-ключ в боковой панели, чтобы начать.")

# -----------------------------
# ФУТЕР
# -----------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <h4>Tips for Best Results</h4>
    <p>
    • Убедитесь, что у вас есть доступ к нужному профилю (не приватный)<br>
    • Укажите несколько недавних постов, если хотите оценить контент<br>
    • Добавьте контекста в поле (для кого профиль, его цель и т.д.)<br>
    • Не бойтесь юмора — мы делаем «прожарку» в конструктивном стиле
    </p>
</div>
""", unsafe_allow_html=True)
