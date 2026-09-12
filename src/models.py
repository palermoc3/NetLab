"""Modelo de dados da coleta."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib


@dataclass
class Noticia:
    titulo: Optional[str]
    resumo: Optional[str]
    data_publicacao: Optional[str]
    url: Optional[str]
    pagina: int
    coletado_em: datetime
    seletor_usado: str = ""

    @property
    def id(self) -> str:
        base = _normalizar_url(self.url) if self.url else (self.titulo or "")
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        d["coletado_em"] = self.coletado_em.isoformat(timespec="seconds")
        return {
            "id": d["id"],
            "titulo": d["titulo"],
            "resumo": d["resumo"],
            "data_publicacao": d["data_publicacao"],
            "url": d["url"],
            "pagina": d["pagina"],
            "coletado_em": d["coletado_em"],
            "seletor_usado": d["seletor_usado"],
        }

    def campos_ausentes(self) -> list:
        campos = ["titulo", "resumo", "data_publicacao", "url"]
        return [c for c in campos if not getattr(self, c)]


def _normalizar_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))
