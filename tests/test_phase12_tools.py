"""Testes das ferramentas locais usadas no portão de hardware."""

from tools.provision_technician import valid_password


def test_technician_password_policy():
    assert valid_password("Senha-forte-123")
    assert not valid_password("curta1A")
    assert not valid_password("sem-maiuscula-123")
    assert not valid_password("SEM-MINUSCULA-123")
    assert not valid_password("SemNumeroAlgum")
