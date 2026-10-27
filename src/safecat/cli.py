"""Linha de comando: ``safecat migrate | import-table | purge``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from safecat.config import get_settings
from safecat.esocial.tables import TabelaESocial, importar_tabela
from safecat.logging_setup import setup_logging


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="safecat", description="Utilitários do SafeCAT AI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("migrate", help="Aplica as migrações do banco (Alembic)")

    imp = sub.add_parser("import-table", help="Importa uma tabela oficial do eSocial (CSV codigo;descricao)")
    imp.add_argument("numero", type=int, choices=[t.value for t in TabelaESocial])
    imp.add_argument("arquivo", type=Path)
    imp.add_argument("--destino", type=Path, default=None, help="Padrão: SAFECAT_TABLES_DIR")

    pur = sub.add_parser("purge", help="Exclui CATs com acidente anterior ao período de retenção")
    pur.add_argument("--older-than-days", type=int, default=None, help="Padrão: SAFECAT_RETENTION_DAYS")

    args = parser.parse_args(argv)
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.cmd == "migrate":
        from safecat.store import migrate

        migrate(settings.database_url)
        print("Migrações aplicadas.")
        return 0

    if args.cmd == "import-table":
        destino = args.destino or settings.tables_dir
        if destino is None:
            print("Informe --destino ou defina SAFECAT_TABLES_DIR.", file=sys.stderr)
            return 2
        try:
            n = importar_tabela(args.arquivo, TabelaESocial(args.numero), destino)
        except (OSError, ValueError) as exc:
            print(f"Erro ao importar: {exc}", file=sys.stderr)
            return 1
        print(f"Tabela {args.numero}: {n} códigos importados em {destino}.")
        return 0

    # purge
    days = args.older_than_days if args.older_than_days is not None else settings.retention_days
    if days <= 0:
        print("Retenção não configurada (SAFECAT_RETENTION_DAYS=0). Nada a fazer.")
        return 0
    from safecat.store import CatRepository, make_engine

    removidos = CatRepository(make_engine(settings.database_url)).purge_older_than(days)
    print(f"{removidos} registro(s) removido(s).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
