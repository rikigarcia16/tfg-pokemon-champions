// Exporta les dades del mod Champions de Showdown a JSON per a l'agent de Python.
// Ús: node tools/export_dex.js > agent/data/champions_dex.json
const path = require('path');
const {Dex} = require(path.join(__dirname, '..', 'showdown', 'dist', 'sim'));

const dex = Dex.mod('champions');
const species = {};
for (const s of dex.species.all()) {
	if (!s.exists) continue;
	species[s.id] = {
		name: s.name,
		types: s.types,
		baseStats: s.baseStats,
		abilities: Object.values(s.abilities),
		weightkg: s.weightkg,
	};
}
const moves = {};
for (const m of dex.moves.all()) {
	if (!m.exists) continue;
	moves[m.id] = {
		name: m.name,
		type: m.type,
		category: m.category,
		basePower: m.basePower,
		accuracy: m.accuracy === true ? 100 : m.accuracy,
		priority: m.priority,
		target: m.target,
		flags: Object.keys(m.flags),
		multihit: m.multihit || null,
		drain: m.drain || null,
		recoil: m.recoil || null,
		boosts: m.boosts || null,
		selfBoost: m.selfBoost?.boosts || m.self?.boosts || null,
		status: m.status || null,
		heal: m.heal || null,
		selfSwitch: !!m.selfSwitch,
	};
}
const typeChart = {};
for (const t of dex.types.all()) {
	// damageTaken: 0 normal, 1 super eficaç, 2 poc eficaç, 3 immune
	typeChart[t.name] = t.damageTaken;
}
process.stdout.write(JSON.stringify({species, moves, typeChart}));
