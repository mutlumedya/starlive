#!/usr/bin/env python3
# main.py - Tüm IPTV Botları Birleşik (GitHub Actions için)
import logging
import re
import asyncio
import sys
import os
import requests
from datetime import datetime
from telegram import Bot
from bs4 import BeautifulSoup
import urllib3
from httpx import Client

# Uyarıları kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# GitHub Secrets'ten al veya environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8539846290:AAGVJJtCnGcfFwOl7uS5eZFQyDrKUHig_3Q')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003661302600')

# Secrets kontrolü
if TELEGRAM_BOT_TOKEN == '8539846290:AAGVJJtCnGcfFwOl7uS5eZFQyDrKUHig_3Q':
    print("HATA: TELEGRAM_BOT_TOKEN ayarlanmamış!")
    print("GitHub Repository -> Settings -> Secrets and variables -> Actions")
    print("TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ekleyin")
    sys.exit(1)

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("iptv_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== ORTAK FONKSİYONLAR ====================

def shorten_url(long_url):
    """URL'yi kısalt"""
    try:
        # 1. Önce is.gd'yi dene
        try:
            response = requests.get(f"https://is.gd/create.php?format=simple&url={requests.utils.quote(long_url)}", timeout=10)
            if response.status_code == 200 and 'http' in response.text:
                return response.text.strip()
        except:
            pass
        
        # 2. Sonra tinyurl.com'u dene
        try:
            response = requests.get(f"http://tinyurl.com/api-create.php?url={requests.utils.quote(long_url)}", timeout=10)
            if response.status_code == 200:
                return response.text.strip()
        except:
            pass
        
        # 3. Son olarak v.gd'yi dene
        try:
            response = requests.get(f"https://v.gd/create.php?format=simple&url={requests.utils.quote(long_url)}", timeout=10)
            if response.status_code == 200 and 'http' in response.text:
                return response.text.strip()
        except:
            pass
        
        return long_url
        
    except Exception as e:
        logger.error(f"URL kısaltma hatası: {e}")
        return long_url

async def send_with_links(bot, chat_id, m3u_content, filename, caption_prefix, bot_name):
    """M3U'yu Telegram'a gönder ve linkleri paylaş"""
    try:
        if not m3u_content or len(m3u_content) < 100:
            logger.warning(f"{bot_name}: Liste boş - gönderilmiyor")
            return False

        # 1. M3U dosyasını Telegram'a yükle
        logger.info(f"{bot_name}: M3U dosyası Telegram'a yükleniyor...")
        message = await bot.send_document(
            chat_id=chat_id,
            document=m3u_content.encode("utf-8"),
            filename=filename,
            caption=f"{caption_prefix}\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # 2. Telegram CDN linkini al
        if hasattr(message.document, 'file_id'):
            file_info = await bot.get_file(message.document.file_id)
            telegram_cdn_url = file_info.file_path
            if telegram_cdn_url.startswith('/'):
                telegram_cdn_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}{telegram_cdn_url}"
            
            logger.info(f"{bot_name}: Telegram CDN Linki alındı")
            
            # 3. Linki kısalt
            short_url = shorten_url(telegram_cdn_url)
            
            # 4. Linkleri paylaş
            link_message = (
                f"🔗 **{bot_name} LİNKLERİ:**\n\n"
                f"📁 **Telegram CDN Linki:**\n"
                f"`{telegram_cdn_url}`\n\n"
                f"🔗 **Kısa Link:**\n"
                f"`{short_url}`\n\n"
                f"📥 **Kullanım:**\n"
                f"1. Kısa linki kopyala\n"
                f"2. IPTV oynatıcına ekle\n"
                f"3. Canlı yayınları izle!\n\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await bot.send_message(
                chat_id=chat_id,
                text=link_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ {bot_name}: Linkler gönderildi!")
            return True
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {bot_name}: Telegram CDN linki alınamadı. Sadece dosya gönderildi."
            )
            return True
        
    except Exception as e:
        logger.error(f"{bot_name} gönderme hatası: {e}")
        return False

# ==================== BOT 1: ANDRO-PANEL ====================

PROXY = "https://proxy.freecdn.workers.dev/?url="
START = "https://taraftariumizle.org/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

CHANNELS = [
    ("androstreamlivebiraz1", 'TR:beIN Sport 1 HD'),
    ("androstreamlivebs1", 'TR:beIN Sport 1 HD'),
    ("androstreamlivebs2", 'TR:beIN Sport 2 HD'),
    ("androstreamlivebs3", 'TR:beIN Sport 3 HD'),
    ("androstreamlivebs4", 'TR:beIN Sport 4 HD'),
    ("androstreamlivebs5", 'TR:beIN Sport 5 HD'),
    ("androstreamlivebsm1", 'TR:beIN Sport Max 1 HD'),
    ("androstreamlivebsm2", 'TR:beIN Sport Max 2 HD'),
    ("androstreamlivess1", 'TR:S Sport 1 HD'),
    ("androstreamlivess2", 'TR:S Sport 2 HD'),
    ("androstreamlivets", 'TR:Tivibu Sport HD'),
    ("androstreamlivets1", 'TR:Tivibu Sport 1 HD'),
    ("androstreamlivets2", 'TR:Tivibu Sport 2 HD'),
    ("androstreamlivets3", 'TR:Tivibu Sport 3 HD'),
    ("androstreamlivets4", 'TR:Tivibu Sport 4 HD'),
    ("androstreamlivesm1", 'TR:Smart Sport 1 HD'),
    ("androstreamlivesm2", 'TR:Smart Sport 2 HD'),
    ("androstreamlivees1", 'TR:Euro Sport 1 HD'),
    ("androstreamlivees2", 'TR:Euro Sport 2 HD'),
    ("androstreamlivetb", 'TR:Tabii HD'),
    ("androstreamlivetb1", 'TR:Tabii 1 HD'),
    ("androstreamlivetb2", 'TR:Tabii 2 HD'),
    ("androstreamlivetb3", 'TR:Tabii 3 HD'),
    ("androstreamlivetb4", 'TR:Tabii 4 HD'),
    ("androstreamlivetb5", 'TR:Tabii 5 HD'),
    ("androstreamlivetb6", 'TR:Tabii 6 HD'),
    ("androstreamlivetb7", 'TR:Tabii 7 HD'),
    ("androstreamlivetb8", 'TR:Tabii 8 HD'),
    ("androstreamliveexn", 'TR:Exxen HD'),
    ("androstreamliveexn1", 'TR:Exxen 1 HD'),
    ("androstreamliveexn2", 'TR:Exxen 2 HD'),
    ("androstreamliveexn3", 'TR:Exxen 3 HD'),
    ("androstreamliveexn4", 'TR:Exxen 4 HD'),
    ("androstreamliveexn5", 'TR:Exxen 5 HD'),
    ("androstreamliveexn6", 'TR:Exxen 6 HD'),
    ("androstreamliveexn7", 'TR:Exxen 7 HD'),
    ("androstreamliveexn8", 'TR:Exxen 8 HD'),
]

def get_src(u, ref=None):
    try:
        if ref:
            HEADERS['Referer'] = ref
        r = requests.get(PROXY + u, headers=HEADERS, verify=False, timeout=20)
        return r.text if r.status_code == 200 else None
    except:
        return None

def generate_andro_m3u():
    try:
        logger.info("Andro-Panel M3U oluşturuluyor...")
        
        h1 = get_src(START)
        if not h1:
            return None

        s = BeautifulSoup(h1, 'html.parser')
        lnk = s.find('link', rel='amphtml')
        if not lnk:
            return None
        amp = lnk.get('href')

        h2 = get_src(amp)
        if not h2:
            return None

        m = re.search(r'\[src\]="appState\.currentIframe".*?src="(https?://[^"]+)"', h2, re.DOTALL)
        if not m:
            return None
        ifr = m.group(1)

        h3 = get_src(ifr, ref=amp)
        if not h3:
            return None

        bm = re.search(r'baseUrls\s*=\s*\[(.*?)\]', h3, re.DOTALL)
        if not bm:
            return None

        cl = bm.group(1).replace('"', '').replace("'", "").replace("\n", "").replace("\r", "")
        srvs = [x.strip() for x in cl.split(',') if x.strip().startswith("http")]
        srvs = list(set(srvs))

        active_servers = []
        tid = "androstreamlivebs1"

        for sv in srvs:
            sv = sv.rstrip('/')
            turl = f"{sv}/{tid}.m3u8" if "checklist" in sv else f"{sv}/checklist/{tid}.m3u8"
            turl = turl.replace("checklist//", "checklist/")
            try:
                HEADERS['Referer'] = ifr
                tr = requests.get(PROXY + turl, headers=HEADERS, verify=False, timeout=5)
                if tr.status_code == 200:
                    active_servers.append(sv)
            except:
                pass

        if not active_servers:
            return None

        lines = ["#EXTM3U"]
        for srv in active_servers:
            for cid, cname in CHANNELS:
                furl = f"{srv}/{cid}.m3u8" if "checklist" in srv else f"{srv}/checklist/{cid}.m3u8"
                furl = furl.replace("checklist//", "checklist/")
                lines.append(f'#EXTINF:-1 tvg-name="{cname}" tvg-logo="https://i.hizliresim.com/8xzjgqv.jpg" group-title="Andro-Panel",{cname}')
                lines.append(furl)

        content = "\n".join(lines)
        content += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | Andro-Panel ({len(active_servers)} aktif sunucu)"
        return content

    except Exception as e:
        logger.error(f"Andro-Panel hatası: {e}")
        return None

async def run_andro_bot(bot, chat_id):
    """Andro-Panel botunu çalıştır"""
    try:
        logger.info("=== ANDRO-PANEL BOTU ÇALIŞIYOR ===")
        m3u_content = generate_andro_m3u()
        if m3u_content:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"andro_panel_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "📺 Andro-Panel Güncel Liste", "Andro-Panel")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ Andro-Panel: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"Andro-Panel bot hatası: {e}")

# ==================== BOT 2: VAVOO TV ====================

DEFAULT_TVG_LOGO_URL = "https://w7.pngwing.com/pngs/1004/75/png-transparent-logo-tv-television-channel-this-tv-tv-shows-miscellaneous-television-heart.png"

def sort_key(tvg_name):
    tvg_name_lower = tvg_name.lower()
    is_bein_spor = "bein" in tvg_name_lower and "spor" in tvg_name_lower
    is_spor = "spor" in tvg_name_lower or "sport" in tvg_name_lower
    
    if is_bein_spor:
        return (0, tvg_name_lower)
    elif is_spor:
        return (1, tvg_name_lower)
    else:
        return (2, tvg_name_lower)

class VavooTVManager:
    def __init__(self):
        self.json_url = "https://www2.vavoo.to/live2/index?countries=all&output=json"
        self.proxy_base = "https://tfms-xyz-4b32.onrender.com/proxy/m3u?url="

    def generate_m3u(self):
        try:
            response = requests.get(self.json_url, timeout=20)
            response.raise_for_status()
            channels = response.json()
        except Exception as e:
            logger.error(f"Vavoo JSON çekilemedi: {e}")
            return "#EXTM3U\n# Hata: Kaynak alınamadı\n"

        turkey_channels = []

        for channel in channels:
            if channel.get("group") != "Turkey":
                continue

            name = channel.get("name", "Bilinmeyen Kanal")
            logo = channel.get("logo") or DEFAULT_TVG_LOGO_URL
            channel_url = channel.get("url", "")
            if not channel_url:
                continue

            stream_url = channel_url.replace("live2/play", "play").replace(".ts", "/index.m3u8")
            proxy_url = f"{self.proxy_base}{stream_url}"

            tvg_id = f"{name.lower().replace(' ', '').replace('.', '')}.tr"

            turkey_channels.append({
                'name': name,
                'tvg_id': tvg_id,
                'logo': logo,
                'proxy_url': proxy_url,
                'sort_priority': sort_key(name)
            })

        turkey_channels.sort(key=lambda x: x['sort_priority'])

        lines = ["#EXTM3U"]
        for ch in turkey_channels:
            lines.append(
                f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" '
                f'tvg-logo="{ch["logo"]}" group-title="Vavoo TV" tvg-country="TR" '
                f'tvg-language="tr",{ch["name"]}'
            )
            lines.append(ch["proxy_url"])

        content = "\n".join(lines)
        content += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | Toplam: {len(turkey_channels)} kanal"
        return content

async def run_vavoo_bot(bot, chat_id):
    """Vavoo TV botunu çalıştır"""
    try:
        logger.info("=== VAVOO TV BOTU ÇALIŞIYOR ===")
        manager = VavooTVManager()
        m3u_content = manager.generate_m3u()
        if m3u_content and len(m3u_content) > 100:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"vavoo_tv_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "📺 Vavoo TV Türkiye Güncel Liste", "Vavoo TV")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ Vavoo TV: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"Vavoo TV bot hatası: {e}")

# ==================== BOT 3: KARMA SPOR ====================

# Dengetv54Manager
class Dengetv54Manager:
    def __init__(self):
        self.httpx = Client(timeout=10, verify=False)
        self.base_stream_url = "https://seven.zirvedesin7.sbs/"
        self.channel_files = {
            1: "yayinzirve.m3u8", 2: "yayin1.m3u8", 3: "yayininat.m3u8", 4: "yayinb2.m3u8",
            5: "yayinb3.m3u8", 6: "yayinb4.m3u8", 7: "yayinb5.m3u8", 8: "yayinbm1.m3u8",
            9: "yayinbm2.m3u8", 10: "yayinss.m3u8", 11: "yayinss2.m3u8", 13: "yayint1.m3u8",
            14: "yayint2.m3u8", 15: "yayint3.m3u8", 16: "yayinsmarts.m3u8", 17: "yayinsms2.m3u8",
            18: "yayintrtspor.m3u8", 19: "yayintrtspor2.m3u8", 20: "yayintrt1.m3u8",
            21: "yayinas.m3u8", 22: "yayinatv.m3u8", 23: "yayintv8.m3u8", 24: "yayintv85.m3u8",
            25: "yayinf1.m3u8", 26: "yayinnbatv.m3u8", 27: "yayineu1.m3u8", 28: "yayineu2.m3u8",
            29: "yayinex1.m3u8", 30: "yayinex2.m3u8", 31: "yayinex3.m3u8", 32: "yayinex4.m3u8",
            33: "yayinex5.m3u8", 34: "yayinex6.m3u8", 35: "yayinex7.m3u8", 36: "yayinex8.m3u8"
        }

    def find_working_domain(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        for i in range(54, 105):
            url = f"https://dengetv{i}.live/"
            try:
                r = self.httpx.get(url, headers=headers)
                if r.status_code == 200 and r.text.strip():
                    return url
            except Exception:
                continue
        return "https://dengetv58.live/"

    def generate_m3u(self):
        referer = self.find_working_domain()
        lines = []
        for _, file_name in self.channel_files.items():
            channel_name = file_name.replace(".m3u8", "").capitalize()
            lines.append(f'#EXTINF:-1 group-title="Dengetv54",{channel_name}')
            lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0')
            lines.append(f'#EXTVLCOPT:http-referrer={referer}')
            lines.append(f'{self.base_stream_url}{file_name}')
        return "\n".join(lines)

# XYZsportsManager
class XYZsportsManager:
    def __init__(self):
        self.httpx = Client(timeout=10, verify=False)
        self.channel_ids = [
            "bein-sports-1", "bein-sports-2", "bein-sports-3", "bein-sports-4", "bein-sports-5",
            "bein-sports-max-1", "bein-sports-max-2", "smart-spor", "smart-spor-2", "trt-spor",
            "trt-spor-2", "aspor", "s-sport", "s-sport-2", "s-sport-plus-1", "s-sport-plus-2"
        ]

    def find_working_domain(self, start=248, end=350):
        headers = {"User-Agent": "Mozilla/5.0"}
        for i in range(start, end + 1):
            url = f"https://www.xyzsports{i}.xyz/"
            try:
                r = self.httpx.get(url, headers=headers)
                if r.status_code == 200 and "uxsyplayer" in r.text:
                    return r.text, url
            except Exception:
                continue
        return None, None

    def find_dynamic_player_domain(self, html):
        m = re.search(r'https?://([a-z0-9\-]+\.[0-9a-z]+\.click)', html)
        return f"https://{m.group(1)}" if m else None

    def extract_base_stream_url(self, html):
        m = re.search(r'this\.baseStreamUrl\s*=\s*[\'"]([^\'"]+)', html)
        return m.group(1) if m else None

    def generate_m3u(self):
        html, referer_url = self.find_working_domain()
        if not html:
            return ""
        player_domain = self.find_dynamic_player_domain(html)
        if not player_domain:
            return ""
        try:
            r = self.httpx.get(f"{player_domain}/index.php?id={self.channel_ids[0]}",
                               headers={"User-Agent": "Mozilla/5.0", "Referer": referer_url})
            base_url = self.extract_base_stream_url(r.text)
            if not base_url:
                return ""
            lines = []
            for cid in self.channel_ids:
                channel_name = cid.replace("-", " ").title()
                lines.append(f'#EXTINF:-1 group-title="XYZSport",{channel_name}')
                lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0')
                lines.append(f'#EXTVLCOPT:http-referrer={referer_url}')
                lines.append(f'{base_url}{cid}/playlist.m3u8')
            return "\n".join(lines)
        except Exception:
            return ""

# TRGOALSManager
class TRGOALSManager:
    def __init__(self):
        self.httpx = Client(timeout=15, verify=False, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)'})

    def get_dynamic_urls(self):
        try:
            redirect_content = self.httpx.get('https://eniyiyayinci.github.io/redirect/index.html').text
            domain_match = re.search(r'URL=(https:\/\/[^"]+)', redirect_content or '')
            dynamic_domain = (domain_match.group(1) if domain_match else 'https://trgoals896.xyz').rstrip('/') + '/'
            channel_content = self.httpx.get(f"{dynamic_domain}channel.html").text
            base_match = re.search(r'const\s+baseurl\s*=\s*["\']([^"\']+)["\']', channel_content or '', re.IGNORECASE)
            base_url = (base_match.group(1) if base_match else 'https://iss.trgoalshls1.shop').rstrip('/') + '/'
            return {'dynamic_domain': dynamic_domain, 'base_url': base_url}
        except Exception:
            return {'dynamic_domain': None, 'base_url': None}

    def generate_m3u(self):
        urls = self.get_dynamic_urls()
        if not urls.get('dynamic_domain') or not urls.get('base_url'):
            return ""

        channels = {
            1: "BEIN SPORTS 1 (ZIRVE)", 2: "BEIN SPORTS 1 (1)", 3: "BEIN SPORTS 1 (INAT)", 4: "BEIN SPORTS 2",
            5: "BEIN SPORTS 3", 6: "BEIN SPORTS 4", 7: "BEIN SPORTS 5", 8: "BEIN SPORTS MAX 1",
            9: "BEIN SPORTS MAX 2", 10: "S SPORT PLUS 1", 11: "S SPORT PLUS 2", 13: "TIVIBU SPOR 1",
            14: "TIVIBU SPOR 2", 15: "TIVIBU SPOR 3", 16: "SPOR SMART 1", 17: "SPOR SMART 2",
            18: "TRT SPOR 1", 19: "TRT SPOR 2", 20: "TRT 1", 21: "A SPOR", 22: "ATV",
            23: "TV 8", 24: "TV 8.5", 25: "FORMULA 1", 26: "NBA TV", 27: "EURO SPORT 1",
            28: "EURO SPORT 2", 29: "EXXEN SPOR 1", 30: "EXXEN SPOR 2", 31: "EXXEN SPOR 3",
            32: "EXXEN SPOR 4", 33: "EXXEN SPOR 5", 34: "EXXEN SPOR 6", 35: "EXXEN SPOR 7",
            36: "EXXEN SPOR 8"
        }
        stream_paths = {
            1: "yayinzirve.m3u8", 2: "yayin1.m3u8", 3: "yayininat.m3u8", 4: "yayinb2.m3u8",
            5: "yayinb3.m3u8", 6: "yayinb4.m3u8", 7: "yayinb5.m3u8", 8: "yayinbm1.m3u8",
            9: "yayinbm2.m3u8", 10: "yayinss.m3u8", 11: "yayinss2.m3u8", 13: "yayint1.m3u8",
            14: "yayint2.m3u8", 15: "yayint3.m3u8", 16: "yayinsmarts.m3u8", 17: "yayinsms2.m3u8",
            18: "yayintrtspor.m3u8", 19: "yayintrtspor2.m3u8", 20: "yayintrt1.m3u8", 21: "yayinas.m3u8",
            22: "yayinatv.m3u8", 23: "yayintv8.m3u8", 24: "yayintv85.m3u8", 25: "yayinf1.m3u8",
            26: "yayinnbatv.m3u8", 27: "yayineu1.m3u8", 28: "yayineu2.m3u8", 29: "yayinex1.m3u8",
            30: "yayinex2.m3u8", 31: "yayinex3.m3u8", 32: "yayinex4.m3u8", 33: "yayinex5.m3u8",
            34: "yayinex6.m3u8", 35: "yayinex7.m3u8", 36: "yayinex8.m3u8"
        }

        lines = []
        for channel_id, channel_name in channels.items():
            if channel_id in stream_paths:
                stream_url = f"{urls['base_url']}{stream_paths[channel_id]}"
                lines.append(f'#EXTINF:-1 group-title="TRGOALS",{channel_name}')
                lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)')
                lines.append(f'#EXTVLCOPT:http-referrer={urls["dynamic_domain"]}')
                lines.append(stream_url)
        return "\n".join(lines)

# SporcafeManager
class SporcafeManager:
    def __init__(self):
        self.httpx = Client(timeout=10, verify=False)
        self.HEADERS = {"User-Agent": "Mozilla/5.0"}
        self.CHANNELS = [
            {"id": "bein1", "source_id": "selcukbeinsports1", "name": "BeIN Sports 1", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/5rhmw31628798883.png", "group": "Spor"},
            {"id": "bein2", "source_id": "selcukbeinsports2", "name": "BeIN Sports 2", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/7uv6x71628799003.png", "group": "Spor"},
            {"id": "bein3", "source_id": "selcukbeinsports3", "name": "BeIN Sports 3", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/u3117i1628798857.png", "group": "Spor"},
            {"id": "bein4", "source_id": "selcukbeinsports4", "name": "BeIN Sports 4", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/2ktmcp1628798841.png", "group": "Spor"},
            {"id": "bein5", "source_id": "selcukbeinsports5", "name": "BeIN Sports 5", "logo": "https://assets.bein.com/mena/sites/3/2015/06/beIN_Sports_5_US.png", "group": "Spor"},
            {"id": "beinmax1", "source_id": "selcukbeinsportsmax1", "name": "BeIN Sports Max 1", "logo": "https://assets.bein.com/mena/sites/3/2015/06/beIN_SPORTS_MAX1_DIGITAL_Mono.png", "group": "Spor"},
            {"id": "beinmax2", "source_id": "selcukbeinsportsmax2", "name": "BeIN Sports Max 2", "logo": "http://tvprofil.com/img/kanali-logo/beIN_Sports_MAX_2_TR_logo_v2.png?1734011568", "group": "Spor"},
            {"id": "tivibu1", "source_id": "selcuktivibuspor1", "name": "Tivibu Spor 1", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/qadnsi1642604437.png", "group": "Spor"},
            {"id": "tivibu2", "source_id": "selcuktivibuspor2", "name": "Tivibu Spor 2", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/kuasdm1642604455.png", "group": "Spor"},
            {"id": "tivibu3", "source_id": "selcuktivibuspor3", "name": "Tivibu Spor 3", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/slwrz41642604502.png", "group": "Spor"},
            {"id": "tivibu4", "source_id": "selcuktivibuspor4", "name": "Tivibu Spor 4", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/59bqi81642604517.png", "group": "Spor"},
            {"id": "ssport1", "source_id": "selcukssport", "name": "S Sport 1", "logo": "https://itv224226.tmp.tivibu.com.tr:6430/images/poster/20230302923239.png", "group": "Spor"},
            {"id": "ssport2", "source_id": "selcukssport2", "name": "S Sport 2", "logo": "https://itv224226.tmp.tivibu.com.tr:6430/images/poster/20230302923321.png", "group": "Spor"},
            {"id": "smart1", "source_id": "selcuksmartspor", "name": "Smart Spor 1", "logo": "https://dsmart-static-v2.ercdn.net//resize-width/1920/content/p/el/11909/Thumbnail.png", "group": "Spor"},
            {"id": "smart2", "source_id": "selcuksmartspor2", "name": "Smart Spor 2", "logo": "https://www.dsmart.com.tr/api/v1/public/images/kanallar/SPORSMART2-gri.png", "group": "Spor"},
            {"id": "aspor", "source_id": "selcukaspor", "name": "A Spor", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/9d28401f-2d4e-4862-85e2-69773f6f45f4.png", "group": "Spor"},
            {"id": "eurosport1", "source_id": "selcukeurosport1", "name": "Eurosport 1", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/54cad412-5f3a-4184-b5fc-d567a5de7160.png", "group": "Spor"},
            {"id": "eurosport2", "source_id": "selcukeurosport2", "name": "Eurosport 2", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/a4cbdd15-1509-408f-a108-65b8f88f2066.png", "group": "Spor"},
        ]

    def find_working_domain(self, start=6, end=100):
        for i in range(start, end + 1):
            url = f"https://www.sporcafe{i}.xyz/"
            try:
                res = self.httpx.get(url, headers=self.HEADERS, timeout=5)
                if res.status_code == 200 and "uxsyplayer" in res.text:
                    return res.text, url
            except Exception:
                continue
        return None, None

    def find_stream_domain(self, html):
        match = re.search(r'https?://(main\.uxsyplayer[0-9a-zA-Z\-]+\.click)', html)
        return f"https://{match.group(1)}" if match else None

    def extract_base_url(self, html):
        match = re.search(r'this\.adsBaseUrl\s*=\s*[\'"]([^\'"]+)', html)
        return match.group(1) if match else None

    def fetch_streams(self, domain, referer):
        result = []
        for ch in self.CHANNELS:
            full_url = f"{domain}/index.php?id={ch['source_id']}"
            try:
                r = self.httpx.get(full_url, headers={**self.HEADERS, "Referer": referer}, timeout=5)
                if r.status_code == 200:
                    base = self.extract_base_url(r.text)
                    if base:
                        stream = f"{base}{ch['source_id']}/playlist.m3u8"
                        result.append((ch, stream))
            except Exception:
                pass
        return result

    def generate_m3u(self):
        html, referer = self.find_working_domain()
        if not html:
            return ""
        stream_domain = self.find_stream_domain(html)
        if not stream_domain:
            return ""
        streams = self.fetch_streams(stream_domain, referer)
        if not streams:
            return ""
        lines = []
        for ch, url in streams:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="Sporcafe",{ch["name"]}')
            lines.append(f'#EXTVLCOPT:http-referrer={referer}')
            lines.append(f'#EXTVLCOPT:http-user-agent={self.HEADERS["User-Agent"]}')
            lines.append(url)
        return "\n".join(lines)

# SalamisTVManager
class SalamisTVManager:
    def __init__(self):
        self.referer_url = "https://yakatv9.live/"
        self.base_stream_url = "https://zinabet.tv"
        self.logo_url = "https://i.hizliresim.com/b6xqz10.jpg"
        self.channels = [
            {"name": "BEIN Sport 1", "id": "701"}, {"name": "BEIN Sport 2", "id": "702"},
            {"name": "BEIN Sport 3", "id": "703"}, {"name": "BEIN Sport 4", "id": "704"},
            {"name": "S Spor", "id": "705"}, {"name": "S Spor 2", "id": "730"},
            {"name": "Tivibu Spor 1", "id": "706"}, {"name": "Tivibu Spor 2", "id": "711"},
            {"name": "Tivibu Spor 3", "id": "712"}, {"name": "Tivibu Spor 4", "id": "713"},
            {"name": "Spor Smart 1", "id": "707"}, {"name": "Spor Smart 2", "id": "708"},
            {"name": "A Spor", "id": "709"}, {"name": "NBA", "id": "nba"}, {"name": "SKYF1", "id": "skyf1"},
        ]

    def generate_m3u(self):
        lines = []
        for channel in self.channels:
            stream_url = f"{self.base_stream_url}/{channel['id']}/mono.m3u8"
            lines.append(f'#EXTINF:-1 tvg-id="spor" tvg-logo="{self.logo_url}" group-title="SalamisTV",{channel["name"]}')
            lines.append(f'#EXTVLCOPT:http-referer={self.referer_url}')
            lines.append(stream_url)
        return "\n".join(lines)

# NexaTVManager
class NexaTVManager:
    def __init__(self):
        self.proxy_prefix = "https://api.codetabs.com/v1/proxy/?quest="
        self.base_stream_url = "https://andro.okan9gote10sokan.cfd/checklist/"
        self.logo_url = "https://i.hizliresim.com/8xzjgqv.jpg"
        self.group_title = "NexaTV"
        self.channels = [
            {"name": "TR:beIN Sport 1 HD", "path": "androstreamlivebs1.m3u8"},
            {"name": "TR:beIN Sport 2 HD", "path": "androstreamlivebs2.m3u8"},
            {"name": "TR:beIN Sport 3 HD", "path": "androstreamlivebs3.m3u8"},
            {"name": "TR:beIN Sport 4 HD", "path": "androstreamlivebs4.m3u8"},
            {"name": "TR:beIN Sport 5 HD", "path": "androstreamlivebs5.m3u8"},
            {"name": "TR:beIN Sport Max 1 HD", "path": "androstreamlivebsm1.m3u8"},
            {"name": "TR:beIN Sport Max 2 HD", "path": "androstreamlivebsm2.m3u8"},
            {"name": "TR:S Sport 1 HD", "path": "androstreamlivess1.m3u8"},
            {"name": "TR:S Sport 2 HD", "path": "androstreamlivess2.m3u8"},
            {"name": "TR:Tivibu Sport HD", "path": "androstreamlivets.m3u8"},
            {"name": "TR:Tivibu Sport 1 HD", "path": "androstreamlivets1.m3u8"},
            {"name": "TR:Tivibu Sport 2 HD", "path": "androstreamlivets2.m3u8"},
            {"name": "TR:Tivibu Sport 3 HD", "path": "androstreamlivets3.m3u8"},
            {"name": "TR:Tivibu Sport 4 HD", "path": "androstreamlivets4.m3u8"},
            {"name": "TR:Smart Sport 1 HD", "path": "androstreamlivesm1.m3u8"},
            {"name": "TR:Smart Sport 2 HD", "path": "androstreamlivesm2.m3u8"},
            {"name": "TR:Euro Sport 1 HD", "path": "androstreamlivees1.m3u8"},
            {"name": "TR:Euro Sport 2 HD", "path": "androstreamlivees2.m3u8"},
            {"name": "TR:Exxen HD", "path": "androstreamliveexn.m3u8"},
            {"name": "TR:Exxen 1 HD", "path": "androstreamliveexn1.m3u8"},
            {"name": "TR:Exxen 2 HD", "path": "androstreamliveexn2.m3u8"},
            {"name": "TR:Exxen 3 HD", "path": "androstreamliveexn3.m3u8"},
            {"name": "TR:Exxen 4 HD", "path": "androstreamliveexn4.m3u8"},
            {"name": "TR:Exxen 5 HD", "path": "androstreamliveexn5.m3u8"},
            {"name": "TR:Exxen 6 HD", "path": "androstreamliveexn6.m3u8"},
            {"name": "TR:Exxen 7 HD", "path": "androstreamliveexn7.m3u8"},
        ]

    def generate_m3u(self):
        lines = []
        for channel in self.channels:
            real_url = f"{self.base_stream_url}{channel['path']}"
            stream_url = f"{self.proxy_prefix}{real_url}"
            lines.append(f'#EXTINF:-1 tvg-id="sport.tr" tvg-name="{channel["name"]}" tvg-logo="{self.logo_url}" group-title="{self.group_title}",{channel["name"]}')
            lines.append(stream_url)
        return "\n".join(lines)

# JustSportHDManager
class JustSportHDManager:
    def __init__(self):
        self.httpx = Client(timeout=10, verify=False)
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
        self.CHANNELS = [
            {"name": "Bein Sports 1", "logo": "bein1.png", "path": "bein1.m3u8"},
            {"name": "Bein Sports 2", "logo": "bein2.png", "path": "bein2.m3u8"},
            {"name": "Bein Sports 3", "logo": "bein3.png", "path": "bein3.m3u8"},
            {"name": "Bein Sports 4", "logo": "bein4.png", "path": "bein4.m3u8"},
            {"name": "Bein Sports 5", "logo": "bein5.png", "path": "bein5.m3u8"},
            {"name": "Exxen Spor", "logo": "exxen.png", "path": "exxen.m3u8"},
            {"name": "S Sport", "logo": "ssport.png", "path": "ssport.m3u8"},
            {"name": "S Sport 2", "logo": "s2sport.png", "path": "ssport2.m3u8"},
            {"name": "S Spor Plus", "logo": "ssportplus.png", "path": "ssportplus.m3u8"},
            {"name": "Spor Smart", "logo": "sporsmart.png", "path": "sporsmart.m3u8"},
            {"name": "Tivibu Spor 1", "logo": "tivibuspor.png", "path": "tivibu1.m3u8"},
            {"name": "Tivibu Spor 2", "logo": "tivibuspor2.png", "path": "tivibu2.m3u8"},
            {"name": "Tivibu Spor 3", "logo": "tivibuspor3.png", "path": "tivibu3.m3u8"},
        ]

    def find_working_domain(self, start=40, end=100):
        headers = {"User-Agent": self.USER_AGENT}
        for i in range(start, end + 1):
            url = f"https://justsporthd{i}.xyz/"
            try:
                r = self.httpx.get(url, headers=headers, timeout=5)
                if r.status_code == 200 and "JustSportHD" in r.text:
                    return r.text, url
            except Exception:
                continue
        return None, None

    def find_stream_domain(self, html):
        match = re.search(r'https?://(streamnet[0-9]+\.xyz)', html)
        return f"https://{match.group(1)}" if match else None

    def generate_m3u(self):
        html, referer_url = self.find_working_domain()
        if not html or not referer_url:
            return ""
        stream_base_url = self.find_stream_domain(html)
        if not stream_base_url:
            return ""
        lines = []
        for channel in self.CHANNELS:
            channel_name = f"{channel['name']} JustSportHD"
            logo_url = f"{referer_url.rstrip('/')}/channel_logo/{channel['logo']}"
            stream_url = f"{stream_base_url}/?url=https://streamcdn.xyz/hls/{channel['path']}"
            lines.append(f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="JustSportHD Liste",{channel_name}')
            lines.append(f'#EXTVLCOPT:http-referer={referer_url}')
            lines.append(f'#EXTVLCOPT:http-user-agent={self.USER_AGENT}')
            lines.append(stream_url)
        return "\n".join(lines)

# KarmaSporManager
class KarmaSporManager:
    def __init__(self):
        self.managers = [
            NexaTVManager(),
            Dengetv54Manager(),
            XYZsportsManager(),
            TRGOALSManager(),
            SporcafeManager(),
            SalamisTVManager(),
            JustSportHDManager()
        ]

    def generate_combined_m3u(self):
        parts = ["#EXTM3U"]
        for manager in self.managers:
            try:
                content = manager.generate_m3u()
                if content.strip():
                    parts.append(content)
            except Exception as e:
                logger.error(f"{manager.__class__.__name__} hatası: {e}")
        final = "\n\n".join(parts)
        final += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | 7 Kaynaktan Karma Spor Listesi"
        return final

async def run_karma_bot(bot, chat_id):
    """Karma Spor botunu çalıştır"""
    try:
        logger.info("=== KARMA SPOR BOTU ÇALIŞIYOR ===")
        manager = KarmaSporManager()
        m3u_content = manager.generate_combined_m3u()
        if m3u_content and len(m3u_content) > 100:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"spor_karma_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "⚽ Spor Karma Güncel Liste", "Karma Spor")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ Karma Spor: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"Karma Spor bot hatası: {e}")

# ==================== BOT 4: TRGOALS ====================

class TRGoalsBot:
    def __init__(self):
        self.httpx = Client(timeout=15, verify=False)

    def redirect_gec(self, url: str) -> str:
        try:
            response = self.httpx.get(url, follow_redirects=True)
            history = [str(r.url).rstrip("/") for r in response.history] + [str(response.url).rstrip("/")]
            for u in reversed(history):
                if "trgoals" in u:
                    return u
            raise ValueError("trgoals içeren URL bulunamadı")
        except Exception as e:
            raise ValueError(f"Redirect hatası: {e}")

    def domain_bul(self) -> str:
        linkler = [
            "https://bit.ly/m/taraftarium24w",
            "https://t.co/aOAO1eIsqE",
            "https://t.co/MTLoNVkGQN"
        ]
        for link in linkler:
            try:
                return self.redirect_gec(link)
            except:
                continue
        return "https://trgoals896.xyz"

    def base_yayin_url_bul(self, domain: str) -> str:
        try:
            resp = self.httpx.get(f"{domain}/channel.html?id=yayin1", follow_redirects=True)
            match = re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', resp.text)
            if match:
                return match.group(1).rstrip("/")
            raise ValueError("baseurl bulunamadı")
        except:
            return "https://iss.trgoalshls1.shop"

    def generate_m3u(self):
        try:
            domain = self.domain_bul()
            logger.info(f"TRGoals Domain: {domain}")
            base_url = self.base_yayin_url_bul(domain)
            logger.info(f"TRGoals Base Yayın URL: {base_url}")

            channels = {
                "BEIN SPORTS 1": "yayin1.m3u8",
                "BEIN SPORTS 2": "yayinb2.m3u8",
                "BEIN SPORTS 3": "yayinb3.m3u8",
                "BEIN SPORTS 4": "yayinb4.m3u8",
                "BEIN SPORTS 5": "yayinb5.m3u8",
                "BEIN MAX 1": "yayinbm1.m3u8",
                "BEIN MAX 2": "yayinbm2.m3u8",
                "S SPORT": "yayinss.m3u8",
                "S SPORT 2": "yayinss2.m3u8",
                "TIVIBU SPOR 1": "yayint1.m3u8",
                "TIVIBU SPOR 2": "yayint2.m3u8",
                "TIVIBU SPOR 3": "yayint3.m3u8",
                "SMART SPOR 1": "yayinsmarts.m3u8",
                "SMART SPOR 2": "yayinsms2.m3u8",
                "A SPOR": "yayinas.m3u8",
                "TRT SPOR": "yayintrtspor.m3u8",
                "EXXEN SPOR 1": "yayinex1.m3u8",
                "EXXEN SPOR 2": "yayinex2.m3u8",
                "EXXEN SPOR 3": "yayinex3.m3u8",
                "EXXEN SPOR 4": "yayinex4.m3u8",
                "EXXEN SPOR 5": "yayinex5.m3u8",
                "EXXEN SPOR 6": "yayinex6.m3u8",
                "EXXEN SPOR 7": "yayinex7.m3u8",
                "EXXEN SPOR 8": "yayinex8.m3u8",
            }

            lines = ["#EXTM3U"]
            for name, path in channels.items():
                stream_url = f"{base_url}/{path}"
                lines.append(f'#EXTINF:-1 group-title="TRGoals",{name}')
                lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0')
                lines.append(f'#EXTVLCOPT:http-referrer={domain}')
                lines.append(stream_url)

            content = "\n".join(lines)
            content += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | TRGoals Güncel"
            return content

        except Exception as e:
            logger.error(f"TRGoals M3U oluşturma hatası: {e}")
            return "#EXTM3U\n# Hata: Güncel domain bulunamadı"

async def run_trgoals_bot(bot, chat_id):
    """TRGoals botunu çalıştır"""
    try:
        logger.info("=== TRGOALS BOTU ÇALIŞIYOR ===")
        trgoals = TRGoalsBot()
        m3u_content = trgoals.generate_m3u()
        if m3u_content and len(m3u_content) > 100:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"trgoals_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "📺 TRGoals Güncel Liste", "TRGoals")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ TRGoals: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"TRGoals bot hatası: {e}")

# ==================== BOT 5: SPORCAFE ====================

SPORCAFE_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}

SPORCAFE_CHANNELS = [
    {"id": "bein1", "source_id": "selcukbeinsports1", "name": "BeIN Sports 1", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/5rhmw31628798883.png"},
    {"id": "bein2", "source_id": "selcukbeinsports2", "name": "BeIN Sports 2", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/7uv6x71628799003.png"},
    {"id": "bein3", "source_id": "selcukbeinsports3", "name": "BeIN Sports 3", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/u3117i1628798857.png"},
    {"id": "bein4", "source_id": "selcukbeinsports4", "name": "BeIN Sports 4", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/2ktmcp1628798841.png"},
    {"id": "bein5", "source_id": "selcukbeinsports5", "name": "BeIN Sports 5", "logo": "https://assets.bein.com/mena/sites/3/2015/06/beIN_Sports_5_US.png"},
    {"id": "beinmax1", "source_id": "selcukbeinsportsmax1", "name": "BeIN Sports Max 1", "logo": "https://assets.bein.com/mena/sites/3/2015/06/beIN_SPORTS_MAX1_DIGITAL_Mono.png"},
    {"id": "beinmax2", "source_id": "selcukbeinsportsmax2", "name": "BeIN Sports Max 2", "logo": "http://tvprofil.com/img/kanali-logo/beIN_Sports_MAX_2_TR_logo_v2.png?1734011568"},
    {"id": "tivibu1", "source_id": "selcuktivibuspor1", "name": "Tivibu Spor 1", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/qadnsi1642604437.png"},
    {"id": "tivibu2", "source_id": "selcuktivibuspor2", "name": "Tivibu Spor 2", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/kuasdm1642604455.png"},
    {"id": "tivibu3", "source_id": "selcuktivibuspor3", "name": "Tivibu Spor 3", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/slwrz41642604502.png"},
    {"id": "tivibu4", "source_id": "selcuktivibuspor4", "name": "Tivibu Spor 4", "logo": "https://r2.thesportsdb.com/images/media/channel/logo/59bqi81642604517.png"},
    {"id": "ssport1", "source_id": "selcukssport", "name": "S Sport 1", "logo": "https://itv224226.tmp.tivibu.com.tr:6430/images/poster/20230302923239.png"},
    {"id": "ssport2", "source_id": "selcukssport2", "name": "S Sport 2", "logo": "https://itv224226.tmp.tivibu.com.tr:6430/images/poster/20230302923321.png"},
    {"id": "smart1", "source_id": "selcuksmartspor", "name": "Smart Spor 1", "logo": "https://dsmart-static-v2.ercdn.net//resize-width/1920/content/p/el/11909/Thumbnail.png"},
    {"id": "smart2", "source_id": "selcuksmartspor2", "name": "Smart Spor 2", "logo": "https://www.dsmart.com.tr/api/v1/public/images/kanallar/SPORSMART2-gri.png"},
    {"id": "aspor", "source_id": "selcukaspor", "name": "A Spor", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/9d28401f-2d4e-4862-85e2-69773f6f45f4.png"},
    {"id": "eurosport1", "source_id": "selcukeurosport1", "name": "Eurosport 1", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/54cad412-5f3a-4184-b5fc-d567a5de7160.png"},
    {"id": "eurosport2", "source_id": "selcukeurosport2", "name": "Eurosport 2", "logo": "https://feo.kablowebtv.com/resize/168A635D265A4328C2883FB4CD8FF/0/0/Vod/HLS/a4cbdd15-1509-408f-a108-65b8f88f2066.png"},
]

def find_sporcafe_working_domain():
    for i in range(6, 101):
        url = f"https://www.sporcafe{i}.xyz/"
        try:
            res = requests.get(url, headers=SPORCAFE_HEADERS, timeout=5)
            if res.status_code == 200 and "uxsyplayer" in res.text:
                logger.info(f"Sporcafe aktif domain: {url}")
                return res.text, url
        except:
            pass
    logger.warning("Sporcafe aktif domain bulunamadı")
    return None, None

def find_sporcafe_stream_domain(html):
    match = re.search(r'https?://(main\.uxsyplayer[0-9a-zA-Z\-]+\.click)', html)
    return f"https://{match.group(1)}" if match else None

def extract_sporcafe_base_url(html):
    match = re.search(r'this\.adsBaseUrl\s*=\s*[\'"]([^\'"]+)', html)
    return match.group(1) if match else None

def generate_sporcafe_m3u():
    try:
        html, referer = find_sporcafe_working_domain()
        if not html:
            return None

        stream_domain = find_sporcafe_stream_domain(html)
        if not stream_domain:
            logger.warning("Sporcafe stream domain bulunamadı")
            return None

        streams = []
        for ch in SPORCAFE_CHANNELS:
            full_url = f"{stream_domain}/index.php?id={ch['source_id']}"
            try:
                r = requests.get(full_url, headers={**SPORCAFE_HEADERS, "Referer": referer}, timeout=8)
                if r.status_code == 200:
                    base = extract_sporcafe_base_url(r.text)
                    if base:
                        stream_url = f"{base}{ch['source_id']}/playlist.m3u8"
                        streams.append((ch, stream_url))
            except:
                pass

        if not streams:
            logger.warning("Sporcafe'den hiç stream alınamadı")
            return None

        lines = ["#EXTM3U"]
        for ch, url in streams:
            lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="Sporcafe",{ch["name"]}')
            lines.append(f"#EXTVLCOPT:http-referrer={referer}")
            lines.append(f"#EXTVLCOPT:http-user-agent={SPORCAFE_HEADERS['User-Agent']}")
            lines.append(url)

        content = "\n".join(lines)
        content += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | Sporcafe Güncel"
        return content

    except Exception as e:
        logger.error(f"Sporcafe M3U hatası: {e}")
        return None

async def run_sporcafe_bot(bot, chat_id):
    """Sporcafe botunu çalıştır"""
    try:
        logger.info("=== SPORCAFE BOTU ÇALIŞIYOR ===")
        m3u_content = generate_sporcafe_m3u()
        if m3u_content and len(m3u_content) > 100:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"sporcafe_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "📺 Sporcafe Güncel Liste", "Sporcafe")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ Sporcafe: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"Sporcafe bot hatası: {e}")

# ==================== BOT 6: YOUTUBE HLS ====================

LINK_TXT_URL = "https://raw.githubusercontent.com/sahind01/cdnmutlubot/refs/heads/main/link.txt"
YOUTUBE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def link_txt_oku():
    try:
        resp = requests.get(LINK_TXT_URL, headers=YOUTUBE_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"link.txt erişilemedi: {resp.status_code}")
            return []
        icerik = resp.text
        logger.info("link.txt başarıyla okundu")
    except Exception as e:
        logger.error(f"link.txt okuma hatası: {e}")
        return []

    kanallar = []
    mevcut_kanal = {}
    for satir in icerik.split('\n'):
        satir = satir.strip()
        if not satir:
            if mevcut_kanal:
                kanallar.append(mevcut_kanal)
                mevcut_kanal = {}
            continue
        if satir.startswith('isim='):
            mevcut_kanal['isim'] = satir[5:]
        elif satir.startswith('içerik='):
            mevcut_kanal['icerik'] = satir[7:]
        elif satir.startswith('logo='):
            mevcut_kanal['logo'] = satir[5:]
    if mevcut_kanal:
        kanallar.append(mevcut_kanal)
    logger.info(f"{len(kanallar)} kanal bulundu")
    return kanallar

def get_youtube_page(url):
    proxy_servers = [
        f"https://corsproxy.io/?{url}",
        f"https://api.allorigins.win/raw?url={requests.utils.quote(url)}",
        f"https://api.codetabs.com/v1/proxy/?quest={url}",
        url
    ]
    for proxy_url in proxy_servers:
        try:
            resp = requests.get(proxy_url, headers=YOUTUBE_HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except:
            continue
    return None

def extract_hls_url(html):
    if not html:
        return None
    patterns = [
        r'"hlsManifestUrl":"(https?://[^"]+)"',
        r'"hlsVp9Url":"(https?://[^"]+)"',
        r'"hlsUrl":"(https?://[^"]+)"',
        r'(https?://manifest\.googlevideo\.com[^"\']*m3u8[^"\']*)',
        r'(https?://[^"\']*youtube\.com[^"\']*m3u8[^"\']*)',
        r'"playbackUrl":"(https?://[^"]+m3u8[^"]*)"',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            hls = matches[0].replace('\\u0026', '&').replace('\\/', '/').replace('\\u002F', '/')
            if 'm3u8' in hls.lower():
                return hls
    return None

def generate_youtube_m3u():
    try:
        kanallar = link_txt_oku()
        if not kanallar:
            return None

        lines = ["#EXTM3U"]
        basarili = 0
        for kanal in kanallar:
            youtube_url = kanal.get('icerik', '')
            name = kanal.get('isim', 'Bilinmeyen')
            logo = kanal.get('logo', '')

            if not youtube_url:
                logger.info(f"URL yok: {name}")
                continue

            logger.info(f"HLS aranıyor: {name} - {youtube_url[:60]}...")
            hls_url = get_youtube_page(youtube_url)
            if hls_url:
                hls_url = extract_hls_url(hls_url)

            if hls_url:
                lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="YouTube Canlı",{name}')
                lines.append(hls_url)
                basarili += 1
                logger.info(f"HLS bulundu: {name}")
            else:
                logger.info(f"HLS bulunamadı: {name} (canlı yayın olmayabilir)")

        if basarili == 0:
            logger.warning("Hiç canlı yayın bulunamadı – liste boş")
            return None

        content = "\n".join(lines)
        content += f"\n\n# Generated: {datetime.utcnow().isoformat()} UTC | YouTube HLS ({basarili}/{len(kanallar)} canlı)"
        return content

    except Exception as e:
        logger.error(f"YouTube M3U hatası: {e}")
        return None

async def run_youtube_bot(bot, chat_id):
    """YouTube HLS botunu çalıştır"""
    try:
        logger.info("=== YOUTUBE HLS BOTU ÇALIŞIYOR ===")
        m3u_content = generate_youtube_m3u()
        if m3u_content and len(m3u_content) > 100:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"youtube_hls_{timestamp}.m3u"
            await send_with_links(bot, chat_id, m3u_content, filename, "📺 YouTube Canlı HLS Liste", "YouTube HLS")
        else:
            await bot.send_message(chat_id=chat_id, text="❌ YouTube HLS: M3U oluşturulamadı!")
    except Exception as e:
        logger.error(f"YouTube HLS bot hatası: {e}")

# ==================== ANA PROGRAM ====================

async def run_all_bots():
    """Tüm botları çalıştır"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Başlangıç mesajı
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🚀 IPTV Botları Başlatıldı\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nTüm botlar sırayla çalıştırılacak..."
        )
        
        # Botları sırayla çalıştır
        bots = [
            (run_andro_bot, "Andro-Panel"),
            (run_vavoo_bot, "Vavoo TV"),
            (run_karma_bot, "Karma Spor"),
            (run_trgoals_bot, "TRGoals"),
            (run_sporcafe_bot, "Sporcafe"),
            (run_youtube_bot, "YouTube HLS")
        ]
        
        for bot_func, bot_name in bots:
            try:
                logger.info(f"Çalıştırılıyor: {bot_name}")
                await bot_func(bot, TELEGRAM_CHAT_ID)
                await asyncio.sleep(5)  # Her bot arasında 5 saniye bekle
            except Exception as e:
                logger.error(f"{bot_name} çalıştırma hatası: {e}")
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"❌ {bot_name} hatası: {str(e)[:100]}")
        
        # Bitiş mesajı
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"✅ Tüm botlar tamamlandı!\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nBir sonraki çalıştırma 40 dakika sonra..."
        )
        
    except Exception as e:
        logger.error(f"Ana program hatası: {e}")

async def main():
    """Ana fonksiyon - 40 dakikada bir çalışır"""
    logger.info("=" * 60)
    logger.info("IPTV BOT SİSTEMİ BAŞLATILDI")
    logger.info(f"Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
    logger.info("=" * 60)
    
    # Sonsuz döngüde 40 dakikada bir çalış
    while True:
        try:
            logger.info(f"Yeni tur başlıyor: {datetime.now().strftime('%H:%M:%S')}")
            await run_all_bots()
            
            # 40 dakika bekle
            logger.info("40 dakika bekleniyor...")
            await asyncio.sleep(40 * 60)  # 40 dakika = 2400 saniye
            
        except KeyboardInterrupt:
            logger.info("Kullanıcı tarafından durduruldu")
            break
        except Exception as e:
            logger.error(f"Ana döngü hatası: {e}")
            # Hata durumunda 5 dakika bekle ve tekrar dene
            await asyncio.sleep(5 * 60)

if __name__ == "__main__":
    # Kontroller
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("HATA: Telegram bot token'ını ayarlayın!")
        print("1. @BotFather'dan bot oluşturun")
        print("2. Token'ı alın ve TELEGRAM_BOT_TOKEN değişkenine yapıştırın")
        sys.exit(1)
    
    if TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("HATA: Chat ID'yi ayarlayın!")
        print("1. @userinfobot'tan chat ID'nizi alın")
        print("2. TELEGRAM_CHAT_ID değişkenine yapıştırın")
        sys.exit(1)
    
    # Programı çalıştır
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program kullanıcı tarafından sonlandırıldı")
    except Exception as e:
        logger.error(f"Kritik hata: {e}")
