"""Top tracked items for price collection.

GW2 API prices are in copper (12345 = 1g 23s 45c).
Item IDs sourced from the GW2 API / wiki.
"""

# High-volume, commonly traded items to poll every 15 minutes
TOP_20_ITEM_IDS: list[int] = [
    19976,  # Mystic Coin
    19721,  # Glob of Ectoplasm
    19685,  # Orichalcum Ore
    19701,  # Orichalcum Ingot
    24295,  # Vial of Powerful Blood (T6)
    24358,  # Ancient Bone (T6)
    24351,  # Powerful Venom Sac (T6)
    24277,  # Pile of Crystalline Dust (T6)
    24299,  # Elaborate Totem (T6)
    24283,  # Armored Scale (T6)
    24300,  # Vicious Claw (T6)
    24289,  # Vicious Fang (T6)
    68063,  # Amalgamated Gemstone
    19675,  # Mithril Ore
    19700,  # Mithril Ingot
    46742,  # Mystic Clover
    46740,  # Gift of Fortune
    19925,  # Deldrimor Steel Ingot
    46745,  # Elonian Leather Square
    19677,  # Elder Wood Log
]

# Extended list for hourly polling (top 20 + additional high-value items)
TOP_200_ITEM_IDS: list[int] = TOP_20_ITEM_IDS + [
    # Precursor weapons
    29169,  # Dawn
    29185,  # Dusk
    29167,  # Spark
    29181,  # Storm
    29180,  # Tooth of Frostfang
    29166,  # Zap
    29175,  # The Legend
    29177,  # The Lover
    29168,  # Howl
    29176,  # The Chosen
    # Ascended materials
    46738,  # Spool of Gossamer Thread (placeholder — ascended crafting)
    46739,  # Spool of Silk Thread (placeholder)
    # Gemstones & upgrades
    24502,  # Superior Rune of the Scholar
    24836,  # Superior Sigil of Force
    # Cooking / consumables
    12134,  # Butter
    12271,  # Pile of Salt
    12236,  # Vanilla Bean
    # Dyes (high volume)
    20852,  # Unidentified Dye
    # Additional T5 materials
    24294,  # Vial of Potent Blood (T5)
    24341,  # Large Bone (T5)
    24350,  # Potent Venom Sac (T5)
    24276,  # Pile of Incandescent Dust (T5)
    24298,  # Intricate Totem (T5)
    24282,  # Large Scale (T5)
    24352,  # Large Claw (T5)
    24288,  # Large Fang (T5)
]
