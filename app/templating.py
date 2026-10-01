"""
Instância única do Jinja2Templates, compartilhada por main.py e por todos os
routers. Precisa ser uma só porque filtros customizados (ex: brnum) são
registrados por instância — se cada arquivo criasse a sua própria, o filtro só
funcionaria onde foi registrado.
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def brnum(value, decimals=0):
    """Formata número no padrão brasileiro: ponto nos milhares, vírgula no decimal."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    s = f"{value:,.{decimals}f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


templates.env.filters["brnum"] = brnum
