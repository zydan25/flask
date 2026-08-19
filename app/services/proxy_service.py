from urllib.parse import urljoin,urlparse
import ipaddress,socket,httpx
class ProxyError(Exception): pass

def _validate_host(host,allowed_hosts,allow_private=False):
    host=(host or '').lower().rstrip('.')
    if allowed_hosts and host not in {h.lower().rstrip('.') for h in allowed_hosts}: raise ProxyError('Target host is not allowlisted')
    if allow_private:return
    try:
        ip=ipaddress.ip_address(socket.gethostbyname(host))
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved: raise ProxyError('Private/loopback target is blocked')
    except socket.gaierror as exc: raise ProxyError('Target host cannot be resolved') from exc

def forward(profile,method,path,query=None,headers=None,json_body=None,allow_private=False):
    target=urljoin(profile.base_url.rstrip('/')+'/',path.lstrip('/')); parsed=urlparse(target); _validate_host(parsed.hostname,profile.allowed_hosts_json or [],allow_private)
    merged=dict(profile.default_headers_json or {})
    for k,v in (headers or {}).items():
        if k.lower() not in {'host','content-length','connection'}: merged[k]=v
    with httpx.Client(timeout=max(1,min(int(profile.timeout_seconds or 20),120)),verify=profile.verify_tls) as client: response=client.request(method.upper(),target,params=query or {},headers=merged,json=json_body)
    try: payload=response.json()
    except Exception: payload=response.text
    return response.status_code,dict(response.headers),payload
