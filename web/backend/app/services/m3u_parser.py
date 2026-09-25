import re
import json

class PlaylistItem:
    def __init__(self):
        self.title = ""
        self.url = ""
        self.tvg_logo = ""
        self.group_title = ""
        self.user_agent = ""
        self.cookie = ""
        self.referer = ""
        self.license_string = ""
        self.headers = {}
        self.is_drm = False

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        item = PlaylistItem()
        item.__dict__.update(data)
        return item

def parse_m3u(content: str):
    lines = content.splitlines()
    items = []
    buf_user_agent = None
    buf_cookie = None
    buf_referer = None
    buf_license_string = None
    buf_attrs = None
    buf_title = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            matches = re.findall(r'([a-zA-Z0-9_-]+)=(\"[^\"]*\"|[^,]+)', line)
            attrs = {m[0]: m[1].strip('"') for m in matches}
            buf_attrs = attrs
            title_split = line.rsplit(',', 1)
            buf_title = title_split[1].strip() if len(title_split) > 1 else "Unknown Channel"
        elif line.startswith("#EXTVLCOPT"):
            if "http-user-agent=" in line:
                buf_user_agent = line.split("http-user-agent=")[1]
            if "http-referrer=" in line:
                buf_referer = line.split("http-referrer=")[1]
        elif line.startswith("#EXTHTTP"):
            try:
                json_str = line.replace("#EXTHTTP:", "")
                data = json.loads(json_str)
                if "cookie" in data:
                    buf_cookie = data["cookie"]
                if "user-agent" in data:
                    buf_user_agent = data["user-agent"]
            except:
                pass
        elif line.startswith("#KODIPROP:inputstream.adaptive.license_key="):
            buf_license_string = line.split("=", 1)[1]
        elif not line.startswith("#"):
            current_item = PlaylistItem()
            if buf_user_agent:
                current_item.user_agent = buf_user_agent
            if buf_cookie:
                current_item.cookie = buf_cookie
            if buf_referer:
                current_item.referer = buf_referer
            if buf_license_string:
                current_item.license_string = buf_license_string
                current_item.is_drm = True
            if buf_attrs:
                if "tvg-logo" in buf_attrs:
                    current_item.tvg_logo = buf_attrs["tvg-logo"]
                if "group-title" in buf_attrs:
                    current_item.group_title = buf_attrs["group-title"]
            if buf_title:
                current_item.title = buf_title

            buf_user_agent = buf_cookie = buf_referer = buf_license_string = buf_attrs = buf_title = None

            full_url_line = line
            if "|" in full_url_line:
                url_parts = full_url_line.split("|")
                current_item.url = url_parts[0]
                params = url_parts[1].split("&")
                for p in params:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        if k.lower() == "user-agent":
                            current_item.user_agent = v
                        elif k.lower() == "referer":
                            current_item.referer = v
                        elif k.lower() == "cookie":
                            current_item.cookie = v
                        else:
                            current_item.headers[k] = v
            else:
                current_item.url = full_url_line
            items.append(current_item)
    return items
