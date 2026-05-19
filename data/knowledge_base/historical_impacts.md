# Historical Price Impacts

Documented examples of patches and events causing significant price movements. These patterns teach the system how GW2's economy reacts to changes.

## Pattern: New Legendary Requiring Specific Material

### Coral Orb — New Legendary Ring "Endless Summer" (February 3, 2026)

- **Before:** Steady ~11s 80c (low-demand crafting material)
- **After patch:** Spiked to ~45s immediately
- **Reason:** New Legendary Ring "Endless Summer" requires 250 Coral Orbs. Previously low-demand item suddenly became essential.
- **Pattern:** Niche materials spike 3-5x when required by new legendary recipes.

### Ball of Charged Mists Essence — New Legendary Ring (May 12, 2026)

- **Before:** Stable ~400g
- **After patch:** Spiked to ~2,000g, now declining
- **Reason:** May 12 update introduced a new legendary ring requiring Gift of the Mistwalker, which needs Ball of Charged Mists Essence or Mistwalker Infusion.
- **Pattern:** High-tier materials with limited supply see extreme spikes (5x+) when added to legendary recipes.

## Pattern: Farm Nerf Reducing Supply

### Glob of Ectoplasm — Visions of Eternity "Magic Mirror" (October-November 2025)

- **Oct 28 (expansion launch):** Ecto at ~34s baseline
- **Nov 16 (peak farming):** Crashed to ~20s
- **Reason:** "Magic Mirror" guaranteed drops of Rare Unidentified Gear, which players mass-salvaged into Ectos, flooding supply.
- **Nov 18 (nerf patch):** "Rewards from obscured chests and seer magic-mirror challenges in Castora have been rebalanced." Ecto immediately recovered to ~28s.
- **Pattern:** New farms that produce salvageable gear crash Ecto prices. Nerfs to those farms cause immediate recovery.

## Pattern: Festival Demand Spike

### Glob of Ectoplasm — Festival of the Four Winds (August 2025)

- **Aug 4 (day before):** ~36s 30c
- **Aug 8 (during festival):** ~50s 60c (+39%)
- **Reason:** Ectos are consumed at festival vendors for Zephyrite Supply Boxes (gambling for rare infusions). Massive demand spike.
- **Pattern:** Four Winds reliably spikes Ecto prices 30-50% every year. Predictable annual trade.

### Wintersday Materials (December 2025)

- **Before (early Dec):** Ecto ~5s 20c for event materials
- **During Wintersday:** Declined to ~3s 20c
- **Reason:** Seasonal supply flood from Wintersday activities. Players farming gifts en masse.
- **Pattern:** Seasonal events flood supply of their specific materials, causing price drops during the event. However, these materials often recover after the event ends.

## Pattern: Expansion/Content Release

### General Pattern for Major Content Releases

- T6 materials and Mystic Coins tend to spike 1-3 days before major patches (speculation buying)
- Prices settle or drop once the actual content is released and supply/demand reaches equilibrium
- Materials specifically named in patch notes see the fastest and largest moves
- Materials indirectly affected (through crafting chains) see delayed, smaller moves

### Berserker's Iron Spear of Air — Janthir Wilds Expansion (2025)

- **Before:** Steady ~1g (low-demand underwater weapon)
- **After expansion launch:** Spiked to ~8g, then slow decline over weeks
- **Reason:** Janthir Wilds allowed all classes to wield spears on land (with correct mastery). Story progression required a spear, and most players didn't own one with desired stats (previously underwater-only). Mass buying on launch day → gradual decline as players acquired spears through gameplay.
- **Pattern:** When an expansion makes a previously niche weapon/armor type universally required, existing supply of that gear type spikes enormously. Prices normalize over weeks as new supply enters through drops and crafting.

## Pattern: Build/Class Balance Changes

### Nerfs and Buffs Affecting Gear Demand

- **Stat combo shifts:** When a balance patch nerfs a popular build's core mechanic, gear with that build's preferred stats can see sell pressure as players swap builds. Conversely, buffed builds create demand for their stat combos. Common PvE stats (Berserker's, Viper's, Celestial) are highest volume; niche stats see more volatile swings.
- **Weapon type changes:** If a class's best weapon changes (e.g., sword nerfed, mace buffed), demand shifts between weapon types with popular stat combos (especially exotic and ascended).
- **Rune/Sigil meta shifts:** Balance patches often change which runes and sigils are BiS (Best in Slot). Superior Rune of the Scholar, Superior Sigil of Force, etc. can spike or crash based on meta shifts.
- **Pattern:** These moves are smaller than legendary material spikes (typically 20-100% rather than 300-500%), but affect a broader range of items. The LLM should watch for class-specific balance notes and connect them to stat-gear demand.
- **Note:** This is a lower-priority signal category for now. Tracking specific stat+weapon combos by item ID is out of scope — the system flags general directional trends (e.g., "demand for Viper's gear may increase") rather than specific TP listings.

## Pattern: Patch Speculation

### Pre-Patch Price Movement

- Experienced traders buy materials 1-3 days before expected patches
- If a patch is announced with specific features (new legendary, balance changes), affected materials spike on announcement
- If patch contents are unknown, universal legendary materials (Mystic Coins, T6, Ectos) see modest speculative buying
- Post-patch: If speculation was correct, prices hold or continue rising. If wrong, quick correction back to baseline.

## Key Takeaways for Signal Generation

1. **New legendary recipes** are the strongest single-event driver of price spikes. Any material newly required will spike 3-10x.
2. **Farm changes** (buffs or nerfs) directly control Ectoplasm and common material supply. Nerfs = price up, buffs = price down.
3. **Festivals** create predictable annual cycles. Four Winds = Ecto up. Wintersday = event mats flood.
4. **The 15% TP tax** means only moves >17.6% are actually profitable to trade on.
5. **Speculation** front-runs patches by 1-3 days. By the time a patch drops, the move may already be priced in.
6. **Supply floods** from new content initially crash prices, then nerfs/rebalancing partially restore them.
7. **Weapon/armor type universality changes** (e.g., spears becoming land weapons) create massive demand spikes for previously niche items. These normalize over weeks.
8. **Balance patches** shift gear demand between stat combos, weapon types, and runes/sigils. Smaller moves but broader impact.
