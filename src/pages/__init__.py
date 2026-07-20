"""Инициализация модуля страниц и компонентов."""

from src.pages.base_component import BaseComponent
from src.pages.gitea_components import GiteaLoginFormComponent, GiteaNavbarComponent

__all__ = ["BaseComponent", "GiteaLoginFormComponent", "GiteaNavbarComponent"]
