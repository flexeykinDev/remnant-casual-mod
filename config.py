# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Every tunable value of the mod. Change a number here and run build.py again."""

# --- loot ---------------------------------------------------------------------------------------
RESOURCE_MULTIPLIER = 100          # scrap, iron, ammo, glowing fragments (drops and merchant stock)
SPECIAL_RESOURCE_QUANTITY = 100    # lumenite crystals and simulacrums per drop
ALWAYS_DROP_TAGS = {"Soldier", "Swarm"}   # enemy tiers that always drop loot
KEEP_IF_AT_LEAST = 1_000_000       # leave the merchant's "infinite" scrap stock alone

# --- combat -------------------------------------------------------------------------------------
DIFFICULTY = {"EnemyHealthScalar": 0.5, "EnemyDamageScalar": 0.4, "ExperienceScalar": 5}
PLAYER = {"HealthMax": 250, "StaminaMax": 200, "StaminaRegen": 100, "StaminaRegenDelay": 0,
          "StaminaEmptyDelay": 0.3, "AmmoMax": 300, "WoundedReviveSpeed": 150}
WEAPON_DAMAGE_MULTIPLIER = 2
WEAPON_AMMO_MULTIPLIER = 2         # clip size and reserve ammo

# --- economy ------------------------------------------------------------------------------------
PRICE_MULTIPLIER = 0.1
SELL_VALUE_SCALAR = 1.0            # sell for the full (reduced) price
RECIPE_COST_DIVISOR = 10           # upgrade and crafting ingredients, never below 1

# --- gear ---------------------------------------------------------------------------------------
TRINKET_EFFECT_MULTIPLIER = 2      # positive bonuses of every ring and amulet
TRINKET_OVERRIDES = {"Trinket_Sagestone": {"ExperienceMod": 500},
                     "Trinket_ScavengersBauble": {"CurrencyMod": 500}}

MOD_POWER_COST_MULTIPLIER = 0.25   # weapon mods charge 4x faster
MOD_EFFECT_MULTIPLIER = 2
MOD_DURATION_MULTIPLIER = 2
MOD_COOLDOWN_MULTIPLIER = 0.5

# --- traits -------------------------------------------------------------------------------------
TRAIT_GROWTH_MULTIPLIER = 3        # level-1 value and per-level growth of every trait
TRAIT_GROWTH_OVERRIDES = {"Trait_ElderKnowledge": 10, "Trait_Scavenger": 10}
TRAIT_MAX_LEVEL = 60               # vanilla 20
TRAIT_MAX_NEGATIVE_PERCENT = 90    # reductions such as Suspicion stay above -90% at max level

# --- consumables --------------------------------------------------------------------------------
CONSUMABLE_DURATION_MULTIPLIER = 10
CONSUMABLE_MAX_DURATION = 36000    # 10 hours
CONSUMABLE_EFFECT_MULTIPLIER = 2
HEAL_OVER_TIME_CONSUMABLES = ("Bloodwort",)   # longer duration would only slow the healing down

# Dragon Heart heals HealScalar x 100 health, a full heal only at vanilla's 100 max health.
ITEM_OVERRIDES = {"Consumable_DragonHeart_Action": {"HealScalar": 10},
                  "Consumable_DragonHeart": {"MaxStackCount": 10}}

# --- build --------------------------------------------------------------------------------------
PAK_NAME = "CasualMod_P.pak"       # the _P suffix makes the engine load it over the game paks
GAME_PAKS = ["pakchunk0-WindowsNoEditor.pak", "pakchunk1-WindowsNoEditor.pak"]
# Only these assets are unpacked from the game, everything else is untouched.
ASSET_FILTERS = ["spawntable", "/_core/stats/", "/items/recipes/", "/items/trinkets/",
                 "/items/mods/", "/items/consumables/", "/items/traits/", "/items/common/"]
