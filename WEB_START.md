# اجرای نسخه HTML/CSS/JavaScript

در این نسخه Streamlit استفاده نمی‌شود. FastAPI هم API و هم فرانت را روی یک پورت
اجرا می‌کند.

```bash
cd ~/NexoraDB/tmp/nexoradb-social-network-analysis
source .venv/bin/activate
set -a
source .env
set +a
python run_web.py
```

سپس فقط این آدرس را باز کنید:

```text
http://127.0.0.1:8100
```

مستندات API:

```text
http://127.0.0.1:8100/docs
```

قبل از اجرا، FastAPI یا Streamlit قبلی را با `Ctrl+C` متوقف کنید تا پورت 8100
آزاد باشد.

