# Open Neuriy Marketplace in Neuriy Chat

1. Install the Python SDK:

```bash
pip install -e ./sdk/python
```

2. Set environment variables in Neuriy Chat:

```bash
NEURIY_MARKETPLACE_URL=http://127.0.0.1:8000
NEURIY_MARKETPLACE_STORE_URL=http://127.0.0.1:5011
```

3. Register this folder / `manifest.json` as a Neuriy Chat plugin.

4. In chat, ask things like:
   - “Search the marketplace for assistants”
   - “Open Code Copilot from Neuriy Marketplace”

The plugin exposes `marketplace_search`, `marketplace_get_app`, `marketplace_list_categories`, and `marketplace_open_app`.
