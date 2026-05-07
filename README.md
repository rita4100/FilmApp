# FilmApp

FilmApp - простое веб-приложение с фильмами. Бэкенд написан на Flask, фронтенд лежит в `frontend/index.html`, база данных уже есть в `backend/films.db`.

## Как запустить через requirements

Открой PowerShell или терминал в папке проекта:

```powershell
cd C:\Users\mishe\FilmApp
```

Создай виртуальное окружение:

```powershell
python -m venv .venv
```

Включи его:

```powershell
.\.venv\Scripts\Activate.ps1
```

Если PowerShell ругается на запуск скриптов, выполни один раз:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Поставь зависимости из `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Запусти приложение:

```powershell
python backend\app.py
```

После запуска открой в браузере:

```text
http://localhost:5000
```

API можно проверить тут:

```text
http://localhost:5000/films
```

## Как пользоваться

На главной странице можно смотреть список фильмов, фильтровать их по жанру, году и рейтингу, открывать карточки фильмов, получать случайный фильм, смотреть топ-10 и пользоваться Mood Matcher.

Для входа администратора:

```text
Логин: admin
Пароль: admin123
```

Обычного пользователя можно создать через кнопку регистрации в интерфейсе.

## Как остановить

В терминале, где запущен Flask, нажми:

```text
Ctrl + C
```

## Если база пустая

В проекте уже лежит база `backend/films.db`. Если нужно создать таблицы заново:

```powershell
python backend\db.py
```

Если нужно заново скачать фильмы из TMDB:

```powershell
python backend\seed.py
```

Для скачивания из TMDB нужен ключ API. Его можно положить в файл `.env` в корне проекта:

```text
TMDB_API_KEY=твой_ключ
```
