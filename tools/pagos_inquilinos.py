"""
Tool: Consulta de pagos mensuales de inquilinos (Google Sheets)
Lee la hoja de pagos del edificio. Cada worksheet es un mes (ej. "Abril").
Autentica al inquilino por ID + nombre + bloque antes de mostrar sus datos.
Usa la misma clave de servicio que la tool de departamentos en alquiler.

Autor: DataPath / Alpha State
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv, find_dotenv
from langchain_core.tools import tool

import gspread

load_dotenv(find_dotenv())

# ============================================
# CONFIGURACIÓN
# ============================================
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_INQUILINO_ID")
SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY")

if not SPREADSHEET_ID:
    raise ValueError(
        "Falta GOOGLE_SHEETS_SPREADSHEET_INQUILINO_ID en .env\n"
        "Es el ID del Google Sheet de pagos de inquilinos."
    )

if not SERVICE_ACCOUNT_KEY:
    raise ValueError(
        "Falta GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY en .env\n"
        "Debe contener el JSON completo del service account."
    )

try:
    _credentials_dict = json.loads(SERVICE_ACCOUNT_KEY)
except json.JSONDecodeError as e:
    raise ValueError(f"GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY no es JSON valido: {e}")

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Columnas que identifican al inquilino (no se muestran como pagos)
_COLS_IDENTIDAD = {"bloque inmobiliario", "id", "responsable de pago / propietario"}

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = gspread.service_account_from_dict(_credentials_dict, scopes=_SCOPES)
    return _client


def _mes_actual() -> str:
    return MESES_ES[datetime.now().month - 1]


def _consultar_pagos(id_inquilino: str, nombre: str, bloque: str, mes: str) -> str:
    try:
        spreadsheet = _get_client().open_by_key(SPREADSHEET_ID)

        # Verificar si el worksheet del mes existe
        worksheets_disponibles = [ws.title for ws in spreadsheet.worksheets()]
        mes_capitalizado = mes.strip().capitalize()

        if mes_capitalizado not in worksheets_disponibles:
            meses_str = ", ".join(worksheets_disponibles)
            return f"MES_NO_DISPONIBLE: {mes_capitalizado}. Meses disponibles: {meses_str}"

        worksheet = spreadsheet.worksheet(mes_capitalizado)
        registros = worksheet.get_all_records()

        if not registros:
            return f"No hay datos registrados para el mes de {mes_capitalizado}."

        # Buscar la fila que matchea los 3 campos (ID exacto, nombre y bloque case-insensitive)
        id_buscado = str(id_inquilino).strip()
        nombre_buscado = nombre.strip().lower()
        bloque_buscado = str(bloque).strip().lower()

        fila_encontrada = None
        for registro in registros:
            id_fila = str(registro.get("ID", "")).strip()
            nombre_fila = str(registro.get("Responsable de Pago / Propietario", "")).strip().lower()
            bloque_fila = str(registro.get("Bloque inmobiliario", "")).strip().lower()

            if id_fila == id_buscado and nombre_buscado in nombre_fila and bloque_buscado == bloque_fila:
                fila_encontrada = registro
                break

        if fila_encontrada is None:
            return "No encontre registros con esos datos. Verifica tu ID, nombre completo y numero de bloque."

        # Formatear solo las columnas de pagos (excluir columnas de identidad)
        nombre_real = fila_encontrada.get("Responsable de Pago / Propietario", nombre)
        bloque_real = fila_encontrada.get("Bloque inmobiliario", bloque)

        respuesta = f"Resumen de pagos de {nombre_real} — Bloque {bloque_real} — {mes_capitalizado}:\n\n"
        for columna, valor in fila_encontrada.items():
            if columna.strip().lower() in _COLS_IDENTIDAD:
                continue
            if str(valor).strip() and str(valor).strip() != "0":
                respuesta += f"  {columna}: {valor}\n"

        return respuesta

    except gspread.exceptions.APIError as e:
        return f"Error al acceder a Google Sheets: {str(e)}"
    except Exception as e:
        return f"Error inesperado al consultar los pagos: {str(e)}"


# ============================================
# TOOL EXPORTABLE
# ============================================
@tool
def consultar_pagos_inquilino(
    id_inquilino: str,
    nombre: str,
    bloque: str,
    mes: str = "",
) -> str:
    """
    Consulta los pagos mensuales de un inquilino del Edificio Rio Sul.
    Usa esta herramienta cuando el usuario pregunte sobre:
    - Sus pagos del mes, cuotas, expensas o gastos del edificio
    - Consumo de agua, luz, servicios, administracion, feriados u otros conceptos
    - Cuanto debe pagar este mes o en un mes especifico

    IMPORTANTE — privacidad: solo muestra datos del inquilino autenticado.
    NUNCA invoca esta tool sin haber recibido los 3 datos de identificacion del usuario.

    Args:
        id_inquilino: ID numerico del inquilino (columna ID en la planilla).
        nombre: Nombre completo del responsable de pago tal como figura en la planilla.
        bloque: Numero de bloque/departamento (ej. "101", "205").
        mes: Mes a consultar en espanol con mayuscula inicial (ej. "Abril", "Julio").
             Si esta vacio, se usa el mes actual.
    """
    mes_consulta = mes.strip() if mes.strip() else _mes_actual()
    print(f"   Consultando pagos: bloque={bloque}, id={id_inquilino}, mes={mes_consulta}")
    return _consultar_pagos(id_inquilino, nombre, bloque, mes_consulta)
