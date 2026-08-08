# برنامه تحلیل شبکه اجتماعی با NexoraDB

یک برنامه‌ی نمایشی ساده شامل:

- بک‌اند FastAPI
- رابط Streamlit
- اتصال خارجی به NexoraDB فقط از طریق Python Driver
- ورود فایل سه‌ستونه
- CRUD کاربران و ارتباط‌های دوطرفه
- نمایش LiveGraph بدون Build روزمره
- اجرای ۱۲ الگوریتم گراف NexoraDB

## معماری

```text
Streamlit (:8501) -> FastAPI خارجی (:8100) -> Python Driver -> NexoraDB API (:8000)
```

این پروژه `DocEngine` یا `GraphManager` را مستقیماً import نمی‌کند. تنها فایل
`backend/nexora_service.py` به دیتابیس دسترسی دارد و از
`from nexoradb.api import connect` استفاده می‌کند.

## ۱. پیش‌نیاز

- Python 3.10
- NexoraDB API در حال اجرا روی پورت 8000
- یک Application Token با scope برابر `query:execute`

## ۲. ساخت محیط و نصب با pip

در Linux/WSL:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

فایل `requirements.txt` شامل `nexoradb==0.1.0` است؛ یعنی دیتابیس مانند یک
کتابخانه‌ی Python با pip نصب می‌شود.

اگر بسته هنوز روی PyPI منتشر نشده است، wheel محلی را نصب کنید و سپس بقیه
نیازمندی‌ها را نصب کنید:

```bash
pip install /path/to/nexoradb-0.1.0-cp310-cp310-manylinux_x86_64.whl
pip install fastapi uvicorn[standard] python-multipart streamlit requests streamlit-agraph
```

## ۳. تنظیم اتصال

```bash
cp .env.example .env
```

مقادیر `.env` را تنظیم و سپس در terminal بارگذاری کنید:

```bash
set -a
source .env
set +a
```

توکن را هرگز commit نکنید.

## ۴. اجرای پروژه

Terminal اول، پس از اجرای NexoraDB API:

```bash
source .venv/bin/activate
python run_backend.py
```

مستندات FastAPI:

```text
http://127.0.0.1:8100/docs
```

Terminal دوم:

```bash
source .venv/bin/activate
streamlit run ui/app.py
```

رابط کاربری:

```text
http://127.0.0.1:8501
```

## ۵. آماده‌سازی دیتابیس

در اولین اجرا، این endpoint را یک بار بزنید:

```bash
curl -X POST http://127.0.0.1:8100/api/v1/setup
```

این عملیات collectionهای `professor_users` و `professor_follows` و گراف Live
به نام `professor_social` را می‌سازد. چون گراف پیش از ورود داده ساخته می‌شود،
هر Insert مستقیماً LiveGraph را به‌روزرسانی می‌کند و `BUILD GRAPH` لازم نیست.

## ۶. فرمت فایل

```text
U01 U02 1
U01 U03 1
```

- ستون اول: کاربر اول
- ستون دوم: کاربر دوم
- ستون سوم: فقط `1`، یعنی رابطه دوطرفه

برای هر سطر، دو document جهت‌دار ذخیره می‌شود: `U01 -> U02` و `U02 -> U01`.

## ۷. تست

```bash
python -m unittest discover -s tests -v
```

برای تست واقعی، ابتدا یک فایل وارد کنید و سپس در UI ایجاد/حذف کاربر و ارتباط و
هر ۱۲ الگوریتم را امتحان کنید.

## نکته‌ی نسخه فعلی NexoraDB

الگوریتم‌های JOB در پاسخ اولیه Driver نتیجه را برمی‌گردانند. این برنامه همان
نتیجه را مصرف می‌کند و `JOB RESULT` را در درخواست HTTP جدا اجرا نمی‌کند، چون هر
درخواست Query API یک Executor تازه می‌سازد.

