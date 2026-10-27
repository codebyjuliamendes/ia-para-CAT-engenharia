from __future__ import annotations

import io
from datetime import datetime

from pypdf import PdfReader

from safecat.ai import DemoAnalyzer
from safecat.config import EmployerSettings
from safecat.domain.models import Cat
from safecat.pdf import NAO_INFORMADO, gerar_pdf_cat


def _texto(pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def test_pdf_minimo_sem_dados_inventados(cat_minima: Cat) -> None:
    pdf = gerar_pdf_cat(cat_minima, EmployerSettings())
    assert pdf.startswith(b"%PDF")
    texto = _texto(pdf)
    assert "Maria da Silva" in texto
    assert "529.982.247-25" in texto
    assert NAO_INFORMADO in texto
    assert "Documento auxiliar" in texto
    assert "eSocial (S-2210)" in texto
    assert "Pendências para o S-2210" in texto
    # Nenhum dado fictício herdado da versão anterior.
    for proibido in ("LinhaMestre", "12.345.678/0001-90", "Operador de Máquinas CNC", "120.43210.89-1", "14:20"):
        assert proibido not in texto


def test_pdf_completo_com_analise_e_empregador(cat_completa: Cat) -> None:
    emp = EmployerSettings(razao_social="Metalúrgica Exemplo Ltda", cnpj="11.222.333/0001-81")
    analise = DemoAnalyzer().analisar(cat_completa.relato)
    pdf = gerar_pdf_cat(
        cat_completa, emp, analise=analise, analise_revisada=False, registro_id=7, gerado_em=datetime(2024, 1, 2, 3, 4)
    )
    texto = _texto(pdf)
    assert "Metalúrgica Exemplo Ltda" in texto
    assert "11222333000181" in texto
    assert "Registro interno nº 7" in texto
    assert "Sugestão automática" in texto
    assert "NÃO revisada" in texto
    assert "modo demonstração" in texto
    assert "S525" in texto
    assert "CRM 123456/SP" in texto
    assert "Nenhuma pendência" in texto


def test_pdf_escapa_marcacao_do_usuario(cat_dados: object) -> None:
    from collections.abc import Callable
    from typing import Any, cast

    dados = cast(Callable[..., dict[str, Any]], cat_dados)
    cat = Cat.model_validate(dados(relato="Texto com <b>tags</b> & símbolos <script>alert(1)</script> no relato."))
    texto = _texto(gerar_pdf_cat(cat, EmployerSettings()))
    assert "<script>" in texto
    assert "&" in texto
