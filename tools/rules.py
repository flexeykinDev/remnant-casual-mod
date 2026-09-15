# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""What the mod changes. plan() picks a rule per asset, each rule edits one open package."""
import math
import os
import re

import config
from . import uasset

RESOURCE_ITEMS = ("Resource_Scraps", "Resource_Rare_", "Ammo_", "GlowingFragment")
SPECIAL_ITEMS = ("LumeniteCrystal", "Simulacrum")
PRICE_TABLES = ("Stats_Items", "Stats_Armor", "Stats_RangedWeapon", "Stats_MeleeWeapon",
                "Stats_Trinkets")
WEAPON_TABLES = ("Stats_RangedWeapon", "Stats_MeleeWeapon")

# Trinket fields where a bigger positive number helps the player...
TRINKET_BENEFIT = re.compile(r"Damage|Crit|Speed|Regen|Health|Stamina|Armor|Resist|Currency|Experience|"
                             r"Metal|Ammo|Lumenite|Lifesteal|Revive|PowerBuildUp|ModPower|Rebate|"
                             r"Reduction|Benevolence|Bonus|Refunded|Accuracy|Heal")
# ...minus downsides, thresholds, timings, stack counters and lower-is-better multipliers.
TRINKET_SKIP = re.compile(r"^Incoming(Damage|DamageMod)$|Threshold|Threat|Aggro|Awareness|Encumbrance|"
                          r"Cost|Missing|Percentage|^(Max)?Stack(s|Count)$|ClampedStacks|StackFrequency|"
                          r"RoundsToMaxStacks|Level$|Frequency|Radius|Distance|Impulse|Angle|Multiplier|"
                          r"^DamageReduction$|^DamageScalar$|MinionDamageScalar|Duration|StatusEffect|"
                          r"SummonedCreatureHealth|Flop|PowerOverride|Gearscore|Tolerance|DropHealth")

MOD_EFFECT_FIELDS = {
    "Damage", "Damage_0", "ImpactDamage", "BlowbackDamage", "OnFireDamage", "DoTDamage", "TotalDamageToDeal",
    "ExplosionDamage", "BleedDoTDamage", "BaseDetonationDamage", "MaxDetonationDamage", "DirectDamage",
    "AOE Damage", "Looping_Caster_AoEDamagePerHit", "HealthMax", "HealthMax_0", "MaxHealth", "Health",
    "CloneHealthMax", "ShieldHealth", "ShieldHealthPct", "MaxLevelShieldHealthPct", "HealthPerSecond",
    "HealthRegen", "PetTheDogHealthRegen", "PetTheDogDamageBoost", "CritChanceMod", "MaxLevelCritChanceMod",
    "DamageMod", "MaxLevelDamageMod", "MinionDamageMod", "MaxLevelMinionDamageMod", "RangedDamageMod",
    "EnemyDefenseReduction", "MaxLevelEnemyDefenseReduction", "CorrosionDamageMod", "AllResistance",
    "MaxLevelAllResistance", "MeleeDamageReduction", "MaxLevelMeleeDamageReduction", "RangedDamageReduction",
    "MaxLevelRangedDamageReduction", "MoveSpeedMod"}
MOD_DURATION_FIELDS = {
    "ModDuration", "ShieldDuration", "MaxLevelDuration", "CloneDuration", "Duration_0", "RattleweedLifeDuration",
    "PetTheDogDamageBoostDuration", "BleedDuration", "OnFireDuration", "DoTDuration", "QuillAttachDuration",
    "MarkDuration"}
MOD_COOLDOWN_FIELDS = {"CooldownDuration", "CooldownTime"}

CONSUMABLE_EFFECT_FIELDS = {
    "MeleeAttackSpeedMod", "MoveSpeedMod", "AimMoveSpeedMod", "ExperienceMod", "ReloadSpeedMod", "FireSpeedMod",
    "FireResistance", "RootResistance", "ShockResistance", "FrostResistance", "CorrosiveResistance",
    "RadiationResistance", "AllResistance", "HealthRegen", "StaminaRegen", "ArmorMod", "CritDamageMod",
    "CritChance", "StaminaMax", "HealthMax"}


def top(export):
    return {p["name"]: p for p in export["props"] if p["depth"] == 0}


def rows(export):
    """Yield (row name, {field: prop}) of a DataTable export."""
    row, fields = None, {}
    for p in export["props"]:
        if p["type"] == "row":
            if row:
                yield row, fields
            row, fields = p["name"][4:], {}
        elif p["depth"] == 1:
            fields[uasset.short_field(p["name"])] = p
    if row:
        yield row, fields


def defaults(a):
    """Top-level numeric properties of the blueprint default objects."""
    for export in a.exports:
        if export["name"].startswith("Default__"):
            for p in export["props"]:
                if p["depth"] == 0 and p["type"] in ("IntProperty", "FloatProperty"):
                    yield p


def set_fields(a, values):
    for p in defaults(a):
        if p["name"] in values:
            value = values[p["name"]]
            a.set(p, value if p["type"] == "IntProperty" else float(value))


def spawn_table(a, _name):
    for n, export in enumerate(a.exports):
        props = top(export)
        tags = set(props.get("Tags", {}).get("value") or [])
        item = str(props.get("ItemBP", {}).get("value") or "").rsplit(".", 1)[-1]
        at = f"[{export['name']}] "

        if item.startswith("Resource_Special_") and any(s in item for s in SPECIAL_ITEMS):
            before = props.get("SpawnPointTags") or props.get("Tags") or props.get("RestrictedTags")
            for field in ("QuantityMin", "QuantityMax"):
                if field in props:
                    a.set(props[field], max(props[field]["value"], config.SPECIAL_RESOURCE_QUANTITY),
                          at + item + " ")
                else:
                    a.insert_int(n, before, field, config.SPECIAL_RESOURCE_QUANTITY, at + item + " ")
            if "Chance" in props and props["Chance"]["value"] < 100:
                a.set(props["Chance"], 100, at + item + " ")
            continue

        if item and any(item.startswith(s) or s in item for s in RESOURCE_ITEMS):
            for field in ("QuantityMin", "QuantityMax"):
                p = props.get(field)
                if p and p["value"] < config.KEEP_IF_AT_LEAST:
                    a.set(p, p["value"] * config.RESOURCE_MULTIPLIER, at + item + " ")
        if "AmmoTypes" in props:  # smart ammo keeps its quantities inside a struct array
            for p in export["props"]:
                if p["depth"] > 0 and p["name"] in ("QuantityMin", "QuantityMax"):
                    a.set(p, p["value"] * config.RESOURCE_MULTIPLIER, at + "ammo ")

        if tags & config.ALWAYS_DROP_TAGS and (item or "AmmoTypes" in props):
            who = at + "/".join(sorted(tags)) + " "
            if "WeightedChanceForNoAmmo" in props:
                a.set(props["WeightedChanceForNoAmmo"], 0.0, who)
            if "Chance" in props:
                a.set(props["Chance"], 100, who)
            elif item:
                a.insert_int(n, props.get("ChanceIncreaseOnFail") or props.get("Tags"), "Chance", 100, who)


def difficulty(a, _name):
    for row, fields in rows(a.exports[0]):
        for field, mult in config.DIFFICULTY.items():
            a.set(fields[field], fields[field]["value"] * mult, f"[difficulty {row}] ")


def character(a, _name):
    for row, fields in rows(a.exports[0]):
        if row != "Player":
            continue
        for field, value in config.PLAYER.items():
            a.set(fields[field], float(value) if fields[field]["type"] == "FloatProperty" else value,
                  "[Player] ")


def stats_table(a, name):
    for row, fields in rows(a.exports[0]):
        for field in ("Value", "ValueInc"):
            p = fields.get(field)
            if p and p["value"] > 0:
                new = p["value"] * config.PRICE_MULTIPLIER
                a.set(p, max(1, round(new)) if p["type"] == "IntProperty" else new, f"[{row}] ")
        sell = fields.get("SellValueScalar")
        # tiny scalars (0.005 on quest rings worth 100000) block sell exploits - keep them
        if sell and 0.1 <= sell["value"] < config.SELL_VALUE_SCALAR:
            a.set(sell, config.SELL_VALUE_SCALAR, f"[{row}] ")
        if name in WEAPON_TABLES:
            if "Damage" in fields:
                a.set(fields["Damage"], fields["Damage"]["value"] * config.WEAPON_DAMAGE_MULTIPLIER,
                      f"[{row}] ")
            for field in ("AmmoPerClip", "MaxAmmo"):
                p = fields.get(field)
                if p and p["value"] > 0:
                    a.set(p, p["value"] * config.WEAPON_AMMO_MULTIPLIER, f"[{row}] ")
        if name == "Stats_Armor" and "Encumbrance" in fields:
            p = fields["Encumbrance"]
            a.set(p, 0.0 if p["type"] == "FloatProperty" else 0, f"[{row}] ")


def recipes(a, _name):
    for export in a.exports:
        for p in export["props"]:
            if p["name"].startswith("Ingredient") and p["name"].endswith("Quantity") and p["value"] > 1:
                a.set(p, max(1, math.ceil(p["value"] / config.RECIPE_COST_DIVISOR)), f"[{export['name']}] ")


def trinket(a, name):
    fixed = {}
    for trinket_name, mods in config.TRINKET_OVERRIDES.items():
        if name in (trinket_name, trinket_name + "_Survival"):
            fixed = mods
    for p in defaults(a):
        if p["name"] in fixed:
            a.set(p, float(fixed[p["name"]]))
        elif p["value"] > 0 and TRINKET_BENEFIT.search(p["name"]) and not TRINKET_SKIP.search(p["name"]):
            a.set(p, p["value"] * config.TRINKET_EFFECT_MULTIPLIER)


def weapon_mod(a, name):
    if "Debuff" in name:  # applied to enemies, a bigger DamageMod there could help them
        return
    cooldown_action = "Cooldown" in name
    for p in defaults(a):
        field, value = p["name"], p["value"]
        if value <= 0:
            continue
        if field == "PowerBasis":
            a.set(p, value * config.MOD_POWER_COST_MULTIPLIER)
        elif field in MOD_COOLDOWN_FIELDS or (cooldown_action and field == "Duration"):
            a.set(p, value * config.MOD_COOLDOWN_MULTIPLIER)
        elif field in MOD_DURATION_FIELDS or (field == "Duration" and name.startswith("Mod_")):
            a.set(p, value * config.MOD_DURATION_MULTIPLIER)
        elif field in MOD_EFFECT_FIELDS and not name.startswith("WeaponProfile_"):
            a.set(p, value * config.MOD_EFFECT_MULTIPLIER)


def trait(a, name):
    """Traits store the level-1 value as X and the per-level growth as XInc.

    Negative trait values are bonuses too (Suspicion cuts damage taken, World Walker cuts stamina
    cost). Scalars built around 1.0 (Vaccine 0.985 / -0.015 per level) are scaled around 1.
    """
    props = {p["name"]: p for p in defaults(a)}
    if "MaxLevel" in props:
        a.set(props["MaxLevel"], config.TRAIT_MAX_LEVEL)
    for field, inc in props.items():
        if not field.endswith("Inc") or field[:-3] not in props:
            continue
        mult = config.TRAIT_GROWTH_OVERRIDES.get(name, config.TRAIT_GROWTH_MULTIPLIER)
        base = props[field[:-3]]
        if abs(base["value"] - (1 + inc["value"])) < 1e-4 and inc["value"] != 0:
            a.set(base, 1 + (base["value"] - 1) * mult)
        else:
            total = base["value"] + inc["value"] * (config.TRAIT_MAX_LEVEL - 1)
            if field.endswith("ModInc") and total < 0:
                mult = max(1, min(mult, config.TRAIT_MAX_NEGATIVE_PERCENT / -total))
            a.set(base, base["value"] * mult)
        a.set(inc, inc["value"] * mult)


def consumable(a, name):
    for p in defaults(a):
        field, value = p["name"], p["value"]
        if value <= 0:
            continue
        if field == "Duration" and not any(s in name for s in config.HEAL_OVER_TIME_CONSUMABLES):
            longer = value * config.CONSUMABLE_DURATION_MULTIPLIER
            a.set(p, float(min(longer, max(value, config.CONSUMABLE_MAX_DURATION))))
        elif field in CONSUMABLE_EFFECT_FIELDS:
            a.set(p, value * config.CONSUMABLE_EFFECT_MULTIPLIER)


def plan(rel_path):
    """Pick the rule for an asset path relative to the game's Content folder."""
    name = os.path.basename(rel_path)[:-7]
    folder = rel_path.replace("\\", "/")
    if "SpawnTable" in name:
        return spawn_table
    if name == "Stats_Scaling_Difficulty":
        return difficulty
    if name == "Stats_Character":
        return character
    if name in PRICE_TABLES:
        return stats_table
    if name.startswith("RecipeList_"):
        return recipes
    if name in config.ITEM_OVERRIDES:
        return lambda a, n: set_fields(a, config.ITEM_OVERRIDES[n])
    if "/Items/Trinkets/" in folder:
        return trinket
    if "/Items/Mods/" in folder:
        return weapon_mod
    if "/Items/Consumables/" in folder:
        return consumable
    if "/Items/Traits/" in folder and name.startswith("Trait_"):
        return trait
    return None
