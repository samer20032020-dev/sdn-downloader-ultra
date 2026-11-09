import urllib.request
import json

url = 'https://www.youtube.com/youtubei/v1/next'
payload = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20240301.00.00",
            "hl": "en",
            "gl": "US"
        }
    },
    "videoId": "dQw4w9WgXcQ",
    "playlistId": "RDdQw4w9WgXcQ"
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
)
with urllib.request.urlopen(req, timeout=10) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    
    def find_all(obj, key):
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    results.append(v)
                results.extend(find_all(v, key))
        elif isinstance(obj, list):
            for it in obj:
                results.extend(find_all(it, key))
        return results

    panels = find_all(res, 'playlistPanelVideoRenderer')
    print("Found playlistPanelVideoRenderer count:", len(panels))
    for idx, p in enumerate(panels[:25], 1):
        vid = p.get('videoId')
        title = p.get('title', {}).get('simpleText') or (p.get('title', {}).get('runs', [{}])[0].get('text') if p.get('title', {}).get('runs') else 'Unknown')
        length = p.get('lengthText', {}).get('simpleText') or ''
        print(f"  {idx}. {title} ({length}) https://www.youtube.com/watch?v={vid}")
