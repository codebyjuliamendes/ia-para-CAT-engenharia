"""Repositório de CATs com cuidados de minimização (LGPD).

* Listagens devolvem CPF mascarado e nunca incluem relato ou CID.
* Logs registram apenas IDs.
* Exclusão definitiva por ID e expurgo por retenção (``purge_older_than``).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Engine, create_engine, delete, event, select
from sqlalchemy.orm import Session, sessionmaker

from safecat.ai.schemas import AnaliseResultado
from safecat.domain.models import Cat, Gravidade, TipoAcidente
from safecat.domain.validators import mask_cpf
from safecat.store.orm import CatRecord

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CatResumo:
    id: int
    nome: str
    cpf_mascarado: str
    setor: str | None
    data_acidente: date
    tipo_acidente: str
    gravidade: str | None
    parte_corpo: str | None
    dias_perdidos: int
    pendencias: int
    analise_revisada: bool


@dataclass(frozen=True, slots=True)
class CatCompleta:
    id: int
    criado_em: datetime
    cat: Cat
    analise: AnaliseResultado | None
    analise_revisada: bool
    revisor: str | None


@dataclass(frozen=True, slots=True)
class LinhaIndicador:
    """Linha mínima para indicadores (sem identificação do trabalhador)."""

    setor: str | None
    data_acidente: date
    tipo_acidente: str
    gravidade: str | None
    parte_corpo: str | None
    dias_perdidos: int


def make_engine(url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA secure_delete=ON")  # sobrescreve páginas apagadas
            cur.close()

    return engine


class CatRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with self._sessions() as session, session.begin():
            yield session

    def add(
        self,
        cat: Cat,
        analise: AnaliseResultado | None = None,
        *,
        analise_revisada: bool = False,
        revisor: str | None = None,
    ) -> int:
        rec = CatRecord(
            nome=cat.trabalhador.nome,
            cpf=cat.trabalhador.cpf,
            setor=cat.trabalhador.setor,
            data_acidente=cat.data_acidente,
            tipo_acidente=int(cat.tipo_acidente),
            tipo_cat=int(cat.tipo_cat),
            gravidade=cat.gravidade.value if cat.gravidade else None,
            parte_codigo=cat.parte_atingida.parte.codigo if cat.parte_atingida else None,
            parte_descricao=cat.parte_atingida.parte.descricao if cat.parte_atingida else None,
            dias_perdidos=cat.dias_perdidos,
            pendencias=len(cat.pendencias_s2210()),
            dados=cat.model_dump(mode="json"),
            analise=analise.model_dump(mode="json") if analise else None,
            analise_revisada=analise_revisada,
            revisor=revisor or None,
        )
        with self._session() as s:
            s.add(rec)
            s.flush()
            new_id = rec.id
        log.info("CAT registrada (id=%s)", new_id)
        return new_id

    def list_resumos(self) -> list[CatResumo]:
        with self._session() as s:
            rows = s.scalars(select(CatRecord).order_by(CatRecord.data_acidente.desc(), CatRecord.id.desc())).all()
            return [
                CatResumo(
                    id=r.id,
                    nome=r.nome,
                    cpf_mascarado=mask_cpf(r.cpf),
                    setor=r.setor,
                    data_acidente=r.data_acidente,
                    tipo_acidente=TipoAcidente(r.tipo_acidente).rotulo,
                    gravidade=Gravidade(r.gravidade).rotulo if r.gravidade else None,
                    parte_corpo=r.parte_descricao,
                    dias_perdidos=r.dias_perdidos,
                    pendencias=r.pendencias,
                    analise_revisada=r.analise_revisada,
                )
                for r in rows
            ]

    def linhas_indicadores(self) -> list[LinhaIndicador]:
        with self._session() as s:
            rows = s.execute(
                select(
                    CatRecord.setor,
                    CatRecord.data_acidente,
                    CatRecord.tipo_acidente,
                    CatRecord.gravidade,
                    CatRecord.parte_descricao,
                    CatRecord.dias_perdidos,
                )
            ).all()
            return [
                LinhaIndicador(
                    setor=r.setor,
                    data_acidente=r.data_acidente,
                    tipo_acidente=TipoAcidente(r.tipo_acidente).rotulo,
                    gravidade=Gravidade(r.gravidade).rotulo if r.gravidade else None,
                    parte_corpo=r.parte_descricao,
                    dias_perdidos=r.dias_perdidos,
                )
                for r in rows
            ]

    def get(self, cat_id: int) -> CatCompleta | None:
        with self._session() as s:
            r = s.get(CatRecord, cat_id)
            if r is None:
                return None
            return CatCompleta(
                id=r.id,
                criado_em=r.criado_em,
                cat=Cat.model_validate(r.dados),
                analise=AnaliseResultado.model_validate(r.analise) if r.analise else None,
                analise_revisada=r.analise_revisada,
                revisor=r.revisor,
            )

    def delete(self, cat_id: int) -> bool:
        with self._session() as s:
            result = s.execute(delete(CatRecord).where(CatRecord.id == cat_id))
            removed = bool(result.rowcount)  # type: ignore[attr-defined]
        if removed:
            log.info("CAT excluída (id=%s)", cat_id)
        return removed

    def purge_older_than(self, days: int, *, today: date | None = None) -> int:
        """Exclui registros cujo acidente ocorreu há mais de ``days`` dias."""
        if days <= 0:
            raise ValueError("days deve ser positivo")
        limite = (today or datetime.now(UTC).date()) - timedelta(days=days)
        with self._session() as s:
            result = s.execute(delete(CatRecord).where(CatRecord.data_acidente < limite))
            count = int(result.rowcount)  # type: ignore[attr-defined]
        log.info("Expurgo por retenção: %s registro(s) removido(s) (anteriores a %s)", count, limite)
        return count
