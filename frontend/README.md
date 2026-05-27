# HNOne Streamlit Frontend

Run the FastAPI backend first:

```bash
cd ../backend
../.venv/bin/uvicorn app.main:app --reload
```

Then run Streamlit:

```bash
cd ../frontend
../.venv/bin/streamlit run app.py
```

The app defaults to `http://127.0.0.1:8000` for the API. You can change it in
the sidebar before logging in.
