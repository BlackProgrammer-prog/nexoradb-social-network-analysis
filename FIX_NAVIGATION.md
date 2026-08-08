# اجرای نسخه اصلاح‌شده رابط

علت صفحه سفید، cache شدن `import ui.app` در اجرای مجدد Streamlit بود.

رابط را با entry point اصلاح‌شده اجرا کنید:

```bash
source .venv/bin/activate
streamlit run run_streamlit.py
```

فایل `run_streamlit.py` در هر rerun بدنه رابط را دوباره اجرا می‌کند؛ بنابراین
تغییر صفحه از منوی کناری دیگر باعث صفحه سفید نمی‌شود.

