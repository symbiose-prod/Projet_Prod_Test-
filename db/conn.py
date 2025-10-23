# db/conn.py
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy import create_engine, text

def _is_internal(host: str | None) -> bool:
    # Host interne Kubernetes chez Kinsta
    return bool(host) and host.endswith(".svc.cluster.local")

def _normalize_scheme(db_url: str) -> str:
    """
    - Remplace postgres:// par postgresql:// (SQLAlchemy 2.x)
    - Ajoute le driver psycopg2 si absent.
    """
    u = urlparse(db_url)
    scheme = u.scheme

    # 1) Remap 'postgres' -> 'postgresql'
    if scheme == "postgres":
        scheme = "postgresql"

    # 2) Ajoute '+psycopg2' s'il n'est pas déjà là
    if scheme == "postgresql":
        scheme = "postgresql+psycopg2"

    return urlunparse((scheme, u.netloc, u.path, u.params, u.query, u.fragment))

def _with_param(url: str, key: str, value: str) -> str:
    u = urlparse(url)
    qs = dict(parse_qsl(u.query, keep_blank_values=True))
    qs[key] = value
    new_query = urlencode(qs)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))

def _build_url() -> str:
    # 0) Si l'admin force un sslmode via l'env, on ignore DB_URL et on reconstruit l'URL
    forced_ssl = os.getenv("DB_SSLMODE")
    if forced_ssl:
        host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST")
        port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
        name = os.getenv("DB_DATABASE") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
        user = os.getenv("DB_USERNAME") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
        pwd  = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}?sslmode={forced_ssl}"

    # 1) Sinon, si Kinsta fournit une URL complète
    raw = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
    if raw:
        url = _normalize_scheme(raw)  # postgres:// -> postgresql+psycopg2://
        host = urlparse(url).hostname
        if _is_internal(host):
            # Endpoint interne Kinsta -> pas d’SSL
            url = _with_param(url, "sslmode", "disable")
        else:
            # Endpoint public -> SSL recommandé si non précisé
            if "sslmode=" not in url:
                url = _with_param(url, "sslmode", "require")
        return url

    # 2) Fallback : reconstruire à partir des morceaux
    host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    name = os.getenv("DB_DATABASE") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
    user = os.getenv("DB_USERNAME") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    pwd  = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

    # Choix du sslmode par défaut selon interne/public
    sslmode = "disable" if _is_internal(host) else "require"

    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}?sslmode={sslmode}"

_ENGINE = None

def engine():
    """Renvoie un moteur SQLAlchemy prêt à l'emploi."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(_build_url(), pool_pre_ping=True)
    return _ENGINE

def run_sql(sql: str, params: dict | None = None):
    """Exécute une requête SQL et renvoie le résultat."""
    with engine().begin() as conn:
        return conn.execute(text(sql), params or {})

def ping():
    """Test de santé : SELECT 1."""
    try:
        _ = run_sql("SELECT 1;")
        return True, "✅ DB OK (SELECT 1)"
    except Exception as e:
        return False, f"❌ Erreur de connexion : {e}"


def _current_dsn() -> str:
    """DSN complet effectivement utilisé (avec mot de passe masqué)."""
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    url = _build_url()
    u = urlparse(url)
    # masque le mot de passe
    netloc = u.netloc
    if "@" in netloc and ":" in netloc.split("@")[0]:
        user_pw, hostpart = netloc.split("@", 1)
        user = user_pw.split(":", 1)[0]
        netloc = f"{user}:***@{hostpart}"
    return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))

def debug_dsn() -> str:
    """Petit résumé sans secret: host + sslmode."""
    from urllib.parse import urlparse, parse_qsl
    u = urlparse(_build_url())
    qs = dict(parse_qsl(u.query))
    return f"host={u.hostname} | sslmode={qs.get('sslmode', '<none>')}"

def whoami() -> str:
    # retourne l'utilisateur que notre DSN utilise
    from urllib.parse import urlparse
    u = urlparse(_build_url())
    user = (u.username or "<none>")
    return f"user={user}"

