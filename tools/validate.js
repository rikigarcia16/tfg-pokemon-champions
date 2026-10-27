// Valida un equip en format paste: node tools/validate.js <format> <fitxer>
const fs = require('fs');
const path = require('path');
const {Teams, TeamValidator} = require(path.join(__dirname, '..', 'showdown', 'dist', 'sim'));

const [format, file] = process.argv.slice(2);
const team = Teams.import(fs.readFileSync(file, 'utf8'));
const problems = TeamValidator.get(format).validateTeam(team);
if (problems?.length) {
	console.log(problems.join('\n'));
	process.exit(1);
}
console.log(`OK: ${file} és legal a ${format}`);
