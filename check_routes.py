import sys
sys.path.insert(0, 'e:/PAN_APP/pan-rag')

from api.voice_main import app

print("Voice Server Routes:")
print("=" * 60)
for route in app.routes:
    methods = getattr(route, 'methods', ['N/A'])
    print(f"{route.path:40} {list(methods)}")
print("=" * 60)
print(f"Total routes: {len(app.routes)}")
