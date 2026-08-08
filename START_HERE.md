# اجرای سریع پروژه

دستورهای زیر را از ریشه همین پوشه اجرا کنید.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

توکن NexoraDB را در `.env` قرار دهید، سپس:

```bash
set -a
source .env
set +a
python run_backend.py
```

در یک terminal دیگر و از همین پوشه:

```bash
source .venv/bin/activate
set -a
source .env
set +a
streamlit run streamlit_app.py
```

آدرس‌ها:

- رابط برنامه: http://127.0.0.1:8501
- مستندات بک‌اند: http://127.0.0.1:8100/docs

