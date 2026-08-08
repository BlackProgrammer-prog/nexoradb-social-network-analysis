# رفع خطای Graph is not built/rendered

نسخه `v2` هنگام اولین درخواست، وضعیت `GRAPH STATUS` را بررسی می‌کند. اگر گراف
هنوز ready نباشد، یک بار projection اولیه را در پشت‌صحنه انجام می‌دهد. پس از آن
تمام CRUDها به‌صورت Live اعمال می‌شوند و Build مجدد وجود ندارد.

اجرا:

```bash
source .venv/bin/activate
set -a
source .env
set +a
python run_web_v2.py
```

سپس:

```text
http://127.0.0.1:8100
```

