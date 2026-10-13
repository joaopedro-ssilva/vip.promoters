"""Cifra dos tokens do Instagram (Fernet), com suporte a rotacao de chave.

TOKEN_ENCRYPTION_KEY cifra; as chaves de TOKEN_ENCRYPTION_KEY_PREVIOUS so decifram. O job
`rotate_encrypted_tokens` do worker recifra tudo com a chave atual; depois disso as chaves
antigas podem sair da configuracao.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import settings

_fernet: MultiFernet | None = None


def _get() -> MultiFernet:
    global _fernet
    if _fernet is None:
        _fernet = MultiFernet([Fernet(k.encode()) for k in settings.encryption_keys])
    return _fernet


def reset_cipher() -> None:
    """Descarta o cifrador em cache (testes e troca de configuracao)."""
    global _fernet
    _fernet = None


def encrypt(value: str) -> str:
    return _get().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _get().decrypt(value.encode()).decode()
    except InvalidToken as exc:  # chave trocada ou dado corrompido
        raise ValueError("token ilegivel") from exc


def rotate(value: str) -> str:
    """Recifra com a chave atual (no-op logico se ja estiver nela)."""
    try:
        return _get().rotate(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("token ilegivel") from exc
