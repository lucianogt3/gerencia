"""Blueprint para interface de enfermagem"""
from flask import Blueprint
from . import routes

# Não é necessário criar outro blueprint aqui, já que importamos de routes
# Este arquivo serve apenas para expor o blueprint
bp = routes.bp