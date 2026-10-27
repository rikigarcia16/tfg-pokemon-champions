"""Genera client/play.pokemonshowdown.com/jugar.html a partir del client de prova.

El client de prova obté el nom d'usuari del servidor d'inicis de sessió oficial, cosa que
falla en local. Amb `--no-security`, el servidor local accepta un nom sense token, així que
aquesta pàgina envia `/trn` directament. Cal tornar-la a generar si es recompila el client.
"""

from pathlib import Path

CLIENT = Path(__file__).resolve().parent.parent / "client" / "play.pokemonshowdown.com"

PATCH = """
\t<script>
\t// TFG: servidor local sense seguretat -> el nom no necessita token del servidor oficial
\tif (!location.search.includes('~~')) location.search = '?~~localhost:8000';
\tPS.user.changeName = function (name) {
\t\tname = this.validateName(name);
\t\tPS.send('/trn ' + name + ',0,');
\t\tthis.update({success: true});
\t};
\t// sense resposta del servidor oficial, el client es queda a "Connectant..."
\tsetTimeout(function () {
\t\tif (PS.user.initializing) {
\t\t\tPS.user.initializing = false;
\t\t\tPS.user.update(null);
\t\t}
\t}, 1500);
\t</script>
</body></html>"""

html = (CLIENT / "testclient-new.html").read_text(encoding="utf-8")
html = html.replace("</body></html>", PATCH, 1)
(CLIENT / "jugar.html").write_text(html, encoding="utf-8")
print(f"Generat {CLIENT / 'jugar.html'}")
