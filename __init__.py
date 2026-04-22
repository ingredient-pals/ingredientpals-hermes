"""IngredientPals Hermes plugin.

Exposes tools for searching, creating, remixing, and publishing recipes on
IngredientPals, plus a bundled skill that teaches the draft -> iterate ->
publish loop and step-by-step cooking mode.

Environment:
    INGREDIENTPALS_API_KEY  (required) — `ipk_...` from ingredientpals.com
    INGREDIENTPALS_BASE_URL (optional) — defaults to https://ingredientpals.com
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import schemas, tools

logger = logging.getLogger(__name__)

_TOOLSET = "ingredientpals"


def register(ctx):
    """Wire schemas to handlers and register the bundled skill."""

    ctx.register_tool(
        name="ingredientpals_search_recipes",
        toolset=_TOOLSET,
        schema=schemas.SEARCH_RECIPES,
        handler=tools.search_recipes,
    )
    ctx.register_tool(
        name="ingredientpals_get_recipe",
        toolset=_TOOLSET,
        schema=schemas.GET_RECIPE,
        handler=tools.get_recipe,
    )
    ctx.register_tool(
        name="ingredientpals_create_recipe_draft",
        toolset=_TOOLSET,
        schema=schemas.CREATE_RECIPE_DRAFT,
        handler=tools.create_recipe_draft,
    )
    ctx.register_tool(
        name="ingredientpals_remix_recipe_draft",
        toolset=_TOOLSET,
        schema=schemas.REMIX_RECIPE_DRAFT,
        handler=tools.remix_recipe_draft,
    )
    ctx.register_tool(
        name="ingredientpals_get_current_draft",
        toolset=_TOOLSET,
        schema=schemas.GET_CURRENT_DRAFT,
        handler=tools.get_current_draft,
    )
    ctx.register_tool(
        name="ingredientpals_discard_draft",
        toolset=_TOOLSET,
        schema=schemas.DISCARD_DRAFT,
        handler=tools.discard_draft,
    )
    ctx.register_tool(
        name="ingredientpals_publish_draft",
        toolset=_TOOLSET,
        schema=schemas.PUBLISH_DRAFT,
        handler=tools.publish_draft,
    )

    # Bundle the skill. Loadable as `skill_view("ingredientpals:recipes")`.
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                try:
                    ctx.register_skill(child.name, skill_md)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to register skill %s: %s", child.name, e)
