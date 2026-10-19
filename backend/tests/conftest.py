"""Configuración de pruebas: variables mínimas antes de importar la app."""

import os

os.environ.setdefault("JWT_SECRET", "clave-solo-para-pruebas-con-al-menos-32-bytes")