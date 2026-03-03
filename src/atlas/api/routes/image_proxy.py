from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import requests
from urllib.parse import urlparse

router = APIRouter()

# IMPORTANTE: whitelist de dominios para evitar SSRF (seguridad)
ALLOWED_HOSTS = {
    "i.imgur.com",
    "images.unsplash.com",
    "cdn.discordapp.com",
    "raw.githubusercontent.com",
    # agrega acá el dominio real que estás intentando usar
    # ejemplo: "static.tradingview.com"
}

@router.get("/image")
def proxy_image(url: str = Query(..., description="Image URL to proxy")):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {host}")

    try:
        # algunos servers requieren headers básicos para no devolverte 403
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        }
        r = requests.get(url, stream=True, timeout=10, headers=headers)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=f"Upstream returned {r.status_code}")

        content_type = r.headers.get("content-type", "image/jpeg")
        return StreamingResponse(r.raw, media_type=content_type)

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")