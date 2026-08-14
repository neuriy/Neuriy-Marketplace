# Neuriy Marketplace Python SDK

Install:

```bash
pip install -e ./sdk/python
```

Configure:

```bash
export NEURIY_MARKETPLACE_URL=http://127.0.0.1:8000
export NEURIY_MARKETPLACE_STORE_URL=http://127.0.0.1:5011
export NEURIY_MARKETPLACE_TOKEN=optional-jwt
```

Use in Neuriy Chat:

```python
from neuriy_marketplace import MarketplaceClient, chat_tools, execute_tool

client = MarketplaceClient()
print(client.search_apps("assistant")[:3])

# Register chat_tools() with Neuriy Chat, then:
result = execute_tool("marketplace_open_app", {"app_id": "..."}, client=client)
```

Also load `../neuriy-chat/manifest.json` as a Neuriy Chat plugin manifest.
