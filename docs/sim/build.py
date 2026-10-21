# Générateurs du plan docs/jambe_leo_s.html (géométrie calculée) et du test de stabilité.
# python3 build.py  → régénère le plan ;  python3 stabilite_pieds.py → tableau des marges des pieds.
import sys
sys.path.insert(0, '.')
import leg
import front
import top
import hip
D = leg.DIMS
G = leg.GROUND

html = r'''<title>Jambe LEO-S</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Mise en page : une planche de dessin technique — plan à l'échelle en tête, puis nomenclature et détails, cartouche en marge */
:root{
  --paper:#f4f6f3; --sheet:#ffffff; --ink:#1c2421; --muted:#5a6661; --rule:#cfd6d1;
  --servo:#2b5d8c; --servo-fill:#dce7f2; --servo2-fill:#e6e0f2; --servo2:#5a4a91;
  --carbon:#2b2e2d; --petg:#e7ece9; --petg-line:#6f7c76; --tpu:#9fb3a8;
  --rod:#b4660f; --spring:#2c8657; --dim:#b8322a; --axis:#8a9690;
  --f-disp:"Barlow Semi Condensed","Arial Narrow",system-ui,sans-serif;
  --f-body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#121816; --sheet:#18201d; --ink:#e3eae6; --muted:#9aa8a1; --rule:#2d3834;
  --servo:#86b4e0; --servo-fill:#1c2b39; --servo2-fill:#262139; --servo2:#b3a5ea;
  --carbon:#c5cec9; --petg:#222c28; --petg-line:#8d9a94; --tpu:#4f6b5d;
  --rod:#e8a656; --spring:#62c891; --dim:#ff7f72; --axis:#6c7973; color-scheme:dark}}
:root[data-theme="dark"]{
  --paper:#121816; --sheet:#18201d; --ink:#e3eae6; --muted:#9aa8a1; --rule:#2d3834;
  --servo:#86b4e0; --servo-fill:#1c2b39; --servo2-fill:#262139; --servo2:#b3a5ea;
  --carbon:#c5cec9; --petg:#222c28; --petg-line:#8d9a94; --tpu:#4f6b5d;
  --rod:#e8a656; --spring:#62c891; --dim:#ff7f72; --axis:#6c7973; color-scheme:dark}
body{background:var(--paper);color:var(--ink);font-family:var(--f-body);font-size:16px;line-height:1.5;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 48px}
.wrap{max-width:1120px;margin:0 auto;display:grid;gap:28px}
header{display:grid;grid-template-columns:1fr auto;gap:16px 32px;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:14px}
h1{font-family:var(--f-disp);font-weight:700;font-size:clamp(28px,5vw,44px);line-height:1;margin:0;letter-spacing:.01em;text-wrap:balance}
.sub{color:var(--muted);margin:6px 0 0;max-width:62ch}
.cartouche{display:grid;grid-template-columns:auto auto;border:1.5px solid var(--ink);font-family:var(--f-mono);font-size:12px}
.cartouche div{padding:4px 10px;border-bottom:1px solid var(--rule)}
.cartouche div:nth-child(odd){color:var(--muted);border-right:1px solid var(--rule);text-transform:uppercase;letter-spacing:.06em;font-size:10.5px;display:flex;align-items:center}
.cartouche div:nth-last-child(-n+2){border-bottom:0}
h2{font-family:var(--f-disp);font-weight:600;font-size:24px;margin:0 0 10px;letter-spacing:.01em;text-wrap:balance}
h3{font-family:var(--f-disp);font-weight:600;font-size:18px;margin:0 0 6px}
p{margin:0 0 10px;max-width:68ch}
section{display:grid;gap:12px}
.sheet{background:var(--sheet);border:1px solid var(--rule);border-radius:4px}
.plan{overflow-x:auto}
.plan-inner{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px;min-width:900px;align-items:start}
.plan svg{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:13.5px;color:var(--muted);padding:0 4px}
.legend span{display:inline-flex;align-items:center;gap:7px}
.sw{width:22px;height:10px;border:1.5px solid var(--ink);display:inline-block;border-radius:2px}
.sw.servo{background:var(--servo-fill);border-color:var(--servo)}
.sw.servo2{background:var(--servo2-fill);border-color:var(--servo2)}
.sw.tube{background:var(--carbon);border-color:var(--carbon)}
.sw.petg{background:var(--petg);border-color:var(--petg-line)}
.sw.rod{background:var(--rod);border-color:var(--rod);height:4px}
.sw.spr{border:0;border-top:2px dashed var(--spring);height:0}
.sw.dim{border:0;border-top:1.5px solid var(--dim);height:0}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:4px;background:var(--sheet)}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-family:var(--f-disp);font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:var(--paper)}
tr:last-child td{border-bottom:0}
td.n,th.n{font-family:var(--f-mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.rep{display:inline-grid;place-items:center;width:24px;height:24px;border:1.5px solid var(--ink);border-radius:50%;font-family:var(--f-mono);font-size:12px}
.cut{font-family:var(--f-mono);font-weight:500;color:var(--dim)}
.details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.det{padding:14px;display:grid;gap:8px;align-content:start}
.det svg{width:100%;height:auto;display:block}
.det p{font-size:14.5px;margin:0}
.note{border-left:3px solid var(--dim);padding:6px 0 6px 14px;color:var(--ink);max-width:76ch}
.ok{color:var(--spring);font-weight:600}.warn{color:var(--rod);font-weight:600}.bad{color:var(--dim);font-weight:600}
@media (max-width:760px){header{grid-template-columns:1fr}.details{grid-template-columns:1fr}}
/* SVG */
svg text{font-family:var(--f-disp)}
.lbl{font-size:7px;fill:var(--ink)} .small{font-size:5.6px;fill:var(--muted)} .cap{font-size:6.4px;fill:var(--muted);letter-spacing:.08em}
.dimt{font-size:6.6px;fill:var(--dim);font-family:var(--f-mono)!important}
.baln{font-size:6.4px;fill:var(--ink);font-family:var(--f-mono)!important}
.bal{fill:var(--sheet);stroke:var(--ink);stroke-width:.8}
.lead{stroke:var(--ink);stroke-width:.4}
.servo{fill:var(--servo-fill);stroke:var(--servo);stroke-width:1.1}
.servo2{fill:var(--servo2-fill);stroke:var(--servo2);stroke-width:1.1}
.horn{fill:var(--sheet);stroke:var(--servo);stroke-width:1}
.pin{fill:var(--ink)}
.fit,.plate,.yoke{fill:var(--petg);stroke:var(--petg-line);stroke-width:.9}
.fitT{fill:var(--petg);fill-opacity:.45;stroke:var(--petg-line);stroke-width:.8;stroke-dasharray:3 1.5}
.arm2{fill:var(--rod);stroke:var(--rod);stroke-width:.4}
.tube{fill:var(--carbon);stroke:var(--carbon);stroke-width:.6}
.tube-in{fill:none;stroke:var(--carbon);stroke-width:.6;stroke-dasharray:2 1.6}
.tpu{fill:var(--tpu);stroke:var(--petg-line);stroke-width:.6}
.rod{fill:var(--rod);stroke:var(--rod);stroke-width:.4}
.rodend{fill:var(--sheet);stroke:var(--rod);stroke-width:1.2}
.arm{stroke:var(--rod);stroke-width:3;stroke-linecap:round}
.cam{fill:none;stroke:var(--spring);stroke-width:.8;stroke-dasharray:3 2}
.bearing{fill:var(--sheet);stroke:var(--ink);stroke-width:.8}
.spr{fill:none;stroke:var(--spring);stroke-width:1.1}
.cable{stroke:var(--spring);stroke-width:.7;stroke-dasharray:1.5 1.2}
.axis{stroke:var(--axis);stroke-width:.45;stroke-dasharray:6 2 1.5 2}
.ground{stroke:var(--ink);stroke-width:1}
.hatch{fill:url(#hatch)}
.hatchline{stroke:var(--muted);stroke-width:.5}
.dim{stroke:var(--dim);stroke-width:.5}
.ext{stroke:var(--dim);stroke-width:.35}
.arrow{fill:var(--dim)}
.glue{fill:url(#glue)}
.arc{fill:none;stroke:var(--spring);stroke-width:.8;stroke-dasharray:3 1.6}
.arcarrow{fill:var(--spring)}
.arct{font-size:6.2px;fill:var(--spring);font-family:var(--f-disp)}
.fitE{fill:var(--petg);fill-opacity:.7;stroke:var(--servo);stroke-width:.9}
.hole{fill:var(--sheet);stroke:var(--servo);stroke-width:.6}
.mini .dimt{font-size:3.4px}.mini .small{font-size:3.4px}.mini .cap{font-size:3.2px;letter-spacing:.06em}
.mini .arct{font-size:3.6px}.mini .dim{stroke-width:.3}.mini .ext{stroke-width:.25}
.mini .servo,.mini .fitE{stroke-width:.6}.mini .fit,.mini .plate,.mini .fitT{stroke-width:.5}.mini .horn{stroke-width:.6}
.hipviews{display:grid;grid-template-columns:1.1fr 1fr;gap:12px}
@media (max-width:760px){.hipviews{grid-template-columns:1fr}}
.tag{fill:var(--sheet);stroke:var(--rod);stroke-width:.7}
.tagt{font-size:5.4px;fill:var(--rod);font-family:var(--f-mono)!important;font-weight:500}
.det.wide{grid-column:1/-1}
.grid{stroke:var(--rule);stroke-width:1}
.tick{font-size:11px;fill:var(--muted);font-family:var(--f-mono)!important}
.foot{fill:var(--petg);stroke:var(--petg-line);stroke-width:1.5}
.foot:hover{stroke:var(--ink);stroke-width:2.5}
.ankle{fill:var(--muted)}
.com{fill:none;stroke:var(--servo);stroke-width:2.5;stroke-linejoin:round}
.zmp{fill:none;stroke:var(--rod);stroke-width:2;stroke-linejoin:round}
.lab-com{font-size:13px;fill:var(--ink)} .lab-zmp{font-size:13px;fill:var(--ink)}
.topwrap{overflow-x:auto;padding:12px}
.topwrap svg{min-width:760px;width:100%;height:auto;display:block}
.sw.com{border:0;border-top:2.5px solid var(--servo);height:0}.sw.zmp{border:0;border-top:2px solid var(--rod);height:0}
.wall{fill:var(--petg);stroke:var(--petg-line);stroke-width:.9}
.bolt{fill:var(--axis);stroke:var(--ink);stroke-width:.5}
.stud{stroke:var(--axis);stroke-width:1.4}
</style>

<div class="wrap">
<header>
  <div>
    <h1>Jambe LEO-S · Rév. F</h1>
    <p class="sub">Plan coté d'une jambe, servos déportés et bielles en parallélogramme. Coupes des tubes carbone,
    fixation de chaque servo, correctifs des articulations à la limite. Rév. F : hanche à 450 mm (segments de 200 mm), tibia en deux tubes et pied
    allégé repris de LEONARDO.</p>
  </div>
  <div class="cartouche" aria-label="Cartouche">
    <div>Projet</div><div>LEO-S bipède</div>
    <div>Pièce</div><div>Jambe ×1</div>
    <div>Rév.</div><div>F · 20/10/2026</div>
    <div>Unités</div><div>mm · kg·cm</div>
    <div>Servos</div><div>4 × STS3215 12 V</div>
  </div>
</header>

<section>
  <h2>Plan</h2>
  <div class="sheet plan"><div class="plan-inner">
    <svg viewBox="-122 -112 278 __SIDEH__" role="img" aria-label="Vue de côté cotée de la jambe : hanche, cuisse de 200 mm, genou, tibia de 200 mm, cheville à 50 mm du sol, pied de 85 mm, servos S3 et S4 déportés avec bielles B1 et B2.">
      <defs>
        <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path class="arrow" d="M0,1 L10,5 L0,9 Z"/></marker>
        <pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="hatchline" x1="0" y1="0" x2="0" y2="4"/></pattern>
        <marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path class="arcarrow" d="M0,1 L10,5 L0,9 Z"/></marker>
      </defs>
      __SIDE__
    </svg>
    <svg viewBox="-140 -110 290 __FRONTH__" role="img" aria-label="Vue de face cotée des deux jambes tendues : servos S1 à S4, tibia en deux tubes Ø10, bielles B1 et B2 côté extérieur, pieds de 55 mm.">
      <defs><marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path class="arrow" d="M0,1 L10,5 L0,9 Z"/></marker>
      <pattern id="hatch2" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="hatchline" x1="0" y1="0" x2="0" y2="4"/></pattern></defs>
      __FRONT__
    </svg>
  </div></div>
  <div class="legend">
    <span><i class="sw servo"></i>servo STS3215 (S1, S2, S3)</span>
    <span><i class="sw servo2"></i>S4, derrière les deux tubes du tibia (S3 de même derrière la cuisse)</span>
    <span><i class="sw tube"></i>tube carbone (pointillé : partie emmanchée)</span>
    <span><i class="sw petg"></i>pièce imprimée PETG</span>
    <span><i class="sw rod"></i>levier et bielle</span>
    <span><i class="sw spr"></i>ressort et câble</span>
    <span><i class="sw dim"></i>cote</span>
  </div>
  <p class="note">Jambe dessinée genou fléchi de 25°, la position de marche. Jambe tendue, la hanche est à <b>450 mm</b> du sol (robot d'environ 0,8 m).
  Les bielles B1 et B2 sont des parallélogrammes : bras du servo = levier de l'articulation = 22 mm, le genou
  reproduit l'angle du servo avec le même couple. Vu de face : S3 est centré derrière le tube de
  cuisse et S4 derrière les deux tubes du tibia ; leurs palonniers sortent côté extérieur, et une entretoise amène
  chaque bras dans le plan de sa bielle (B1 à 35 mm de l'axe de jambe, B2 à 27 mm). Rien ne dépasse de plus de 32 mm
  vers l'intérieur : 26 mm entre les jambes aux hanches, 25 mm entre les pieds. Largeur hors tout aux bielles : 160 mm.</p>
</section>

<section>
  <h2>Coupes des tubes et bielles</h2>
  <div class="tw"><table>
    <thead><tr><th>Rep.</th><th>Pièce</th><th>Matière</th><th class="n">Entraxe</th><th class="n">Visible</th><th class="n">Longueur de coupe</th></tr></thead>
    <tbody>
      <tr><td><span class="rep">5</span></td><td>Tube de cuisse</td><td>carbone Ø12 × 10</td><td class="n">200</td><td class="n">__TV__</td><td class="n cut">__TC__</td></tr>
      <tr><td><span class="rep">10</span></td><td>Tubes de tibia, côte à côte à 20 mm d'entraxe</td><td>2 × carbone Ø10 × 8</td><td class="n">200</td><td class="n">__SV__</td><td class="n cut">2 × __SC__</td></tr>
      <tr><td><span class="rep">7</span></td><td>Bielle de genou B1</td><td>carbone Ø4 × 2 + 2 goujons M3</td><td class="n">__B1__</td><td class="n">—</td><td class="n cut">__B1C__</td></tr>
      <tr><td><span class="rep">11</span></td><td>Bielle de cheville B2</td><td>carbone Ø4 × 2 + 2 goujons M3</td><td class="n">__B2__</td><td class="n">—</td><td class="n cut">__B2C__</td></tr>
    </tbody>
  </table></div>
  <p>Tubes : chaque bout entre de <b>20 mm</b> dans sa pièce imprimée (d'où coupe = visible + 40). Le tibia passe de
  1 tube Ø12 à <b>2 tubes Ø10 × 8</b> : deux Ø8 auraient été deux fois plus souples d'avant en arrière qu'un Ø12 ; deux Ø10
  gardent la même raideur dans ce sens, sont nettement plus raides en torsion et sur le côté, pour environ 4 g de plus. Bielles : coupe =
  entraxe − 2 × 16 mm, pour des rotules M3 dont le centre de la boule est à 16 mm du bout du tube une fois vissée.
  Mesure tes rotules avant de couper, et garde 2 à 3 mm de filetage libre pour régler la longueur exacte.
  Avec des bielles de 128 et 133 mm, le tube Ø4 × 2 suffit, mais sa marge au flambage baisse d'environ 40 % par rapport
  aux segments de 170 : un tube Ø5 × 3 est plus confortable si tu en trouves.</p>
</section>

<section>
  <h2>Nomenclature et fixation</h2>
  <div class="tw"><table>
    <thead><tr><th>Rep.</th><th>Élément</th><th>Comment il est fixé</th></tr></thead>
    <tbody>
      <tr><td><span class="rep">1</span></td><td>Plaque de bassin, PETG 8 mm</td><td>Porte les deux S1 et le buste. 90 mm entre les axes de hanche.</td></tr>
      <tr><td><span class="rep">2</span></td><td>S1, hanche roulis</td><td>Dans un berceau vissé sous la plaque, arbre vers l'avant, tenu par les 2 trous de coin du bout opposé à l'arbre sur chaque face. Le palonnier tient la plaque avant de l'étrier ; la plaque arrière tourne sur le <b>moyeu arrière</b> du servo (vis M3 + rondelle). Détail I.</td></tr>
      <tr><td><span class="rep">3</span></td><td>S2, hanche tangage</td><td>Sous le plancher de l'étrier, dans un berceau qui ne tient que sa moitié arrière (4 vis M2 dans les trous de coin du bout opposé à l'arbre). La chape en U de la cuisse prend le palonnier côté extérieur et le <b>moyeu arrière</b> côté intérieur. Détail I.</td></tr>
      <tr><td><span class="rep">4</span></td><td>Raccord haut de cuisse + berceau de S3</td><td>Pièce unique en PETG. S3 centré <b>derrière le tube</b>, 4 vis boîtier, arbre à 40 mm sous la hanche et 25 mm en arrière. Palonnier côté extérieur + entretoise de 11,5 mm jusqu'au plan de B1.</td></tr>
      <tr><td><span class="rep">5</span></td><td>Tube de cuisse</td><td>Emmanché 20 mm en haut (4) et en bas (6), collier fendu + vis M3 de serrage, puis époxy une fois réglé.</td></tr>
      <tr><td><span class="rep">6</span></td><td>Chape de genou + came r 20</td><td>Deux joues sur la cuisse, un 625ZZ dans chaque, vis épaulée M5 + écrou frein. La came est solidaire du tibia.</td></tr>
      <tr><td><span class="rep">7</span></td><td>Bielle B1, côté extérieur</td><td>Extrémité <b>a</b> sur le bras de S3, extrémité <b>b</b> sur le levier du genou (joue extérieure du tibia). Plan à 35 mm de l'axe de jambe. Montage : détail H.</td></tr>
      <tr><td><span class="rep">8</span></td><td>Ressorts de genou, 2 × traction</td><td>Devant la cuisse, un au droit de chaque joue du tibia. Ancrés en haut sur un axe M3 du raccord de cuisse, câble Dyneema jusqu'au profil de came (rayon 20) de chaque joue, réglé par un tendeur M3. Mous jusqu'à 10° de flexion. Specs : détail G.</td></tr>
      <tr><td><span class="rep">9</span></td><td>S4, cheville, dans le raccord haut de tibia</td><td>Centré <b>derrière les deux tubes</b>, 4 vis boîtier, arbre à 35 mm sous le genou et 25 mm en arrière de l'axe du tibia. Palonnier côté extérieur + entretoise de 3,5 mm pour amener le bras dans le plan de B2. Ce raccord porte aussi les joues et le levier du genou.</td></tr>
      <tr><td><span class="rep">10</span></td><td>2 tubes de tibia Ø10</td><td>Côte à côte, 20 mm d'entraxe (vue E). Chaque tube entre de 20 mm dans le raccord haut et dans la chape de cheville, collier M3, époxy.</td></tr>
      <tr><td><span class="rep">11</span></td><td>Bielle B2, côté extérieur</td><td>Extrémité <b>c</b> sur le bras de S4, extrémité <b>d</b> sur le levier de talon (joue extérieure du pied, 22 mm derrière la cheville). Plan à 27 mm de l'axe de jambe, derrière les tubes. Montage : détail H.</td></tr>
      <tr><td><span class="rep">12</span></td><td>Chape de cheville + pied évidé</td><td>Deux joues sur le pied, 2 × 625ZZ, vis épaulée M5. Pied de <b>100 × 65 mm</b> (35 derrière l'axe, 65 devant, dimensionné par le test de stabilité), PETG évidé en treillis, ≈ 22 g. Joues de cheville à ±19–25 mm de l'axe.</td></tr>
      <tr><td><span class="rep">13</span></td><td>Semelle TPU 3–4 mm</td><td>Collée sous le pied, ≈ 10 g. Place pour 4 capteurs de force ; leurs fils remontent en boucle souple autour de la cheville.</td></tr>
    </tbody>
  </table></div>
</section>

<section>
  <h2>Interface du STS3215</h2>
  <div class="sheet det">
    <svg class="mini" style="max-width:640px" viewBox="__SVB__" role="img" aria-label="Face arbre du STS3215 : 45,2 × 24,7 mm, arbre à 10,2 mm du bout, 4 trous de coin en rectangle 24,5 × 20,5, 4 petits trous en carré de 9,9 autour de l'arbre ; vue de côté : 35 mm, arbre 25 dents, moyeu arrière Ø6 avec trou M3.">
      __SERVO__
    </svg>
    <p>Cotes relevées sur le modèle 3D du servo publié par le projet SO-ARM100 (précision ±0,2 mm) : <b>mesure ton
    servo au pied à coulisse avant d'imprimer les poches</b>. Les 4 trous de coin Ø1,5 traversent tout le boîtier : ce sont
    ceux des vis de boîtier. Vérifie si elles ressortent sur la face qui te sert ; si oui, on les remplace par des vis M2 plus
    longues qui traversent aussi le berceau. Les 4 petits trous Ø2,5 autour de l'arbre ne font que 2,5 mm de profondeur :
    ne compte pas dessus pour porter la jambe.</p>
    <p><b>Règle de fixation, pour les 4 servos :</b> le berceau tient le servo par la <b>moitié opposée à l'arbre</b>, avec les
    2 trous de coin de ce bout, sur les deux faces (4 vis). La moitié côté arbre reste libre : le palonnier et le bras
    tournent sans rien toucher. En face du palonnier, la pièce entraînée s'appuie sur le <b>moyeu arrière</b> Ø6 du servo
    (vis M3 + rondelle) : l'effort passe par les deux côtés du boîtier.</p>
  </div>
</section>

<section>
  <h2>Fixation des servos</h2>
  <p>Deux règles pour tous les servos. Le boîtier est tenu dans une poche imprimée par ses propres trous de fixation,
  jamais par des colliers ou de la colle. Et chaque articulation porte la charge sur des roulements : l'arbre du servo
  ne fait que tourner, il ne soutient pas le robot.</p>
  <div class="details">
    <div class="sheet det wide">
      <h3>I · Hanche : S1, étrier de roulis, S2</h3>
      <div class="hipviews">
        <svg class="mini" viewBox="__HSVB__" role="img" aria-label="Hanche vue de côté : plaque de bassin, berceau de S1, S1 arbre vers l'avant, étrier avec plaque avant sur le palonnier et plaque arrière sur le moyeu arrière, plancher, berceau de S2, S2 dont l'axe est 63,5 mm sous celui de S1.">
          __HSIDE__
        </svg>
        <svg class="mini" viewBox="__HFVB__" role="img" aria-label="Hanche vue de face : S1 avec arbre à 10,2 mm de son bout intérieur, berceau de S1 côté extérieur, étrier en col autour de l'axe de roulis, S2 et chape en U de la cuisse de 49 mm, roulis de −20° à +30°.">
          __HFRONT__
        </svg>
      </div>
      <p><b>Fixe :</b> la plaque de bassin porte le <b>berceau de S1</b> (4 vis M3 dans des inserts). Il tient S1 par son bout
      extérieur, arbre vers l'avant. <b>Mobile en roulis :</b> l'<b>étrier</b> est une pièce en U. Sa plaque avant est vissée
      sur le palonnier de S1 ; sa plaque arrière tourne sur le moyeu arrière de S1 (vis M3 + rondelle). En haut, les deux
      plaques se réduisent à un moyeu de rayon 11 autour de l'axe de roulis, pour ne pas toucher le berceau de S1 en
      tournant de −20° à +30°. En bas, un plancher relie les deux plaques et porte le <b>berceau de S2</b>, qui tient S2 par sa
      moitié arrière. <b>Mobile en tangage :</b> la chape en U de la cuisse (49 mm de large) prend le palonnier de S2 côté
      extérieur et son moyeu arrière côté intérieur. Axe de roulis 63,5 mm au-dessus de l'axe de tangage.</p>
    </div>
    <div class="sheet det">
      <h3>A · Berceau sur le tube</h3>
      <svg viewBox="0 0 170 92" role="img" aria-label="Coupe : tube carbone dans un collier fendu serré par une vis M3, berceau qui entoure le servo, vissé dans le boîtier.">
        <circle class="fit" cx="38" cy="46" r="16"/>
        <rect x="35.5" y="28" width="5" height="8" style="fill:var(--sheet)"/>
        <line class="bolt" x1="26" y1="31" x2="50" y2="31" style="stroke-width:2.2;stroke:var(--axis)"/>
        <circle class="tube" cx="38" cy="46" r="6"/><circle cx="38" cy="46" r="5" style="fill:var(--sheet)"/>
        <rect class="fit" x="54" y="22" width="76" height="48" rx="2"/>
        <rect class="servo" x="60" y="27" width="64" height="38" rx="2"/>
        <line class="lead" x1="50" y1="46" x2="54" y2="46"/>
        <circle class="pin" cx="66" cy="31" r="1.4"/><circle class="pin" cx="118" cy="31" r="1.4"/>
        <circle class="pin" cx="66" cy="61" r="1.4"/><circle class="pin" cx="118" cy="61" r="1.4"/>
        <text class="small" x="20" y="80">tube Ø12, collier</text>
        <text class="small" x="20" y="87">fendu + vis M3</text>
        <text class="small" x="70" y="80">poche + 0,2 mm, 4 vis</text>
        <text class="small" x="70" y="87">dans les trous du boîtier</text>
        <text class="small" x="134" y="48">STS3215</text>
      </svg>
      <p>S3 et S4 vivent dans le raccord imprimé, pas sur le tube nu. Le tube entre de 20 mm dans le raccord, un collier
      fendu le serre (vis M3), et une goutte d'époxy le bloque une fois la jambe réglée.</p>
    </div>
    <div class="sheet det">
      <h3>B · Articulation motorisée (S1, S2)</h3>
      <svg viewBox="0 0 170 92" role="img" aria-label="Coupe : étrier à deux parois, servo d'un côté avec palonnier vissé à la pièce entraînée, palier 625ZZ et vis épaulée M5 de l'autre côté.">
        <rect class="wall" x="8" y="14" width="8" height="64"/>
        <rect class="wall" x="150" y="14" width="8" height="64"/>
        <rect class="servo" x="18" y="28" width="35" height="36" rx="2"/>
        <rect class="horn" x="53" y="34" width="5" height="24" rx="1"/>
        <rect class="fit" x="58" y="30" width="76" height="32" rx="2"/>
        <rect class="bearing" x="150" y="38" width="8" height="16"/>
        <line class="bolt" x1="128" y1="46" x2="164" y2="46" style="stroke-width:4;stroke:var(--axis)"/>
        <rect class="bolt" x="158" y="40" width="5" height="12"/>
        <line class="axis" x1="4" y1="46" x2="166" y2="46"/>
        <circle class="pin" cx="62" cy="38" r="1.2"/><circle class="pin" cx="62" cy="54" r="1.2"/>
        <text class="small" x="18" y="22">servo dans l'étrier</text>
        <text class="small" x="60" y="72">pièce entraînée, vissée au palonnier</text>
        <text class="small" x="60" y="79">(4 vis sur le pourtour + vis centrale)</text>
        <text class="small" x="104" y="22">moyeu arrière + vis M3</text>
      </svg>
      <p>Le palonnier aluminium du STS3215 se visse sur un flasque de la pièce entraînée. En face, la pièce tourne sur le
      moyeu arrière Ø6 du servo, tenue par une vis M3 et une rondelle : l'effort passe par les deux côtés du boîtier, pas par
      l'arbre seul (dessiné ici avec une paroi pour la lisibilité).</p>
    </div>
    <div class="sheet det">
      <h3>C · Articulation passive (genou, cheville)</h3>
      <svg viewBox="0 0 170 92" role="img" aria-label="Coupe : chape à deux joues avec un roulement 625ZZ dans chaque joue, languette du tibia au milieu, vis épaulée M5 et écrou frein.">
        <rect class="wall" x="30" y="16" width="14" height="60"/>
        <rect class="wall" x="122" y="16" width="14" height="60"/>
        <rect class="fit" x="48" y="24" width="70" height="44" rx="2"/>
        <rect class="bearing" x="32" y="38" width="10" height="16"/>
        <rect class="bearing" x="124" y="38" width="10" height="16"/>
        <line class="bolt" x1="24" y1="46" x2="146" y2="46" style="stroke-width:4;stroke:var(--axis)"/>
        <rect class="bolt" x="18" y="39" width="6" height="14"/>
        <rect class="bolt" x="140" y="40" width="7" height="12"/>
        <line class="axis" x1="10" y1="46" x2="160" y2="46"/>
        <text class="small" x="26" y="11">joues de la chape (cuisse)</text>
        <text class="small" x="54" y="62">languette du tibia + levier 22</text>
        <text class="small" x="12" y="86">vis épaulée M5</text>
        <text class="small" x="64" y="86">2 × 625ZZ</text>
        <text class="small" x="120" y="86">écrou frein M5</text>
      </svg>
      <p>Mêmes pièces au genou et à la cheville : 2 roulements 625ZZ, une vis épaulée M5, un écrou frein, une rondelle
      de chaque côté de la languette. Aucun servo n'est sur ces axes : ils sont entraînés par les bielles.</p>
    </div>
    <div class="sheet det">
      <h3>D · Bielle</h3>
      <svg viewBox="0 0 170 92" role="img" aria-label="Bielle : rotule M3 vissée sur un goujon collé dans un tube carbone de 4 mm, avec un contre-écrou ; entraxe __B1__, coupe __B1C__.">
        <defs><pattern id="glue" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="hatchline" x1="0" y1="0" x2="0" y2="3"/></pattern></defs>
        <circle class="rodend" cx="14" cy="44" r="7"/><circle class="pin" cx="14" cy="44" r="1.8"/>
        <rect class="rod" x="21" y="42" width="9" height="4" style="fill:var(--axis);stroke:var(--axis)"/>
        <rect class="bolt" x="27" y="39.5" width="3" height="9"/>
        <rect class="rod" x="30" y="41" width="110" height="6"/>
        <rect class="glue" x="30" y="41" width="12" height="6"/><rect class="glue" x="128" y="41" width="12" height="6"/>
        <rect class="bolt" x="140" y="39.5" width="3" height="9"/>
        <rect class="rod" x="143" y="42" width="6" height="4" style="fill:var(--axis);stroke:var(--axis)"/>
        <circle class="rodend" cx="156" cy="44" r="7"/><circle class="pin" cx="156" cy="44" r="1.8"/>
        <line class="dim" x1="14" y1="20" x2="156" y2="20" marker-start="url(#ar)" marker-end="url(#ar)"/>
        <line class="ext" x1="14" y1="17" x2="14" y2="36"/><line class="ext" x1="156" y1="17" x2="156" y2="36"/>
        <text class="dimt" x="85" y="16" text-anchor="middle">entraxe __B1__ (B1)</text>
        <line class="dim" x1="30" y1="62" x2="140" y2="62" marker-start="url(#ar)" marker-end="url(#ar)"/>
        <line class="ext" x1="30" y1="50" x2="30" y2="65"/><line class="ext" x1="140" y1="50" x2="140" y2="65"/>
        <text class="dimt" x="85" y="72" text-anchor="middle">coupe __B1C__</text>
        <line class="dim" x1="14" y1="62" x2="30" y2="62"/>
        <text class="dimt" x="22" y="72" text-anchor="middle">16</text>
        <text class="small" x="30" y="86">goujon M3 collé 12 mm à l'époxy · contre-écrou · rotule métal</text>
      </svg>
      <p>Un tube carbone Ø4 × 2, un goujon M3 collé dans chaque bout, une rotule métal vissée et bloquée par un contre-écrou.
      Effort maxi environ 70 N au genou : prends des rotules métal, le plastique prend du jeu.</p>
    </div>
    <div class="sheet det">
      <h3>E · Coupe du tibia sous le genou</h3>
      <svg viewBox="0 0 170 92" role="img" aria-label="Coupe du tibia : deux tubes Ø10 à 20 mm d'entraxe, S4 centré derrière, bielle B2 côté extérieur à 28 mm de l'axe.">
        <rect class="fit" x="44" y="8" width="64" height="62" rx="5" style="fill-opacity:.45;stroke-dasharray:3 2"/>
        <circle class="tube" cx="66" cy="18" r="5"/><circle cx="66" cy="18" r="4" style="fill:var(--sheet)"/>
        <circle class="tube" cx="86" cy="18" r="5"/><circle cx="86" cy="18" r="4" style="fill:var(--sheet)"/>
        <rect class="servo2" x="58.5" y="30.6" width="35" height="24.7" rx="2"/>
        <rect class="horn" x="93.5" y="37" width="4" height="12"/>
        <rect class="arm2" x="97.5" y="41" width="9" height="4"/>
        <circle class="rodend" cx="104" cy="66" r="3"/>
        <line class="axis" x1="76" y1="4" x2="76" y2="80"/>
        <line class="dim" x1="66" y1="5" x2="86" y2="5" marker-start="url(#ar)" marker-end="url(#ar)"/>
        <text class="dimt" x="58" y="7" text-anchor="end">20</text>
        <line class="dim" x1="76" y1="80" x2="104" y2="80" marker-start="url(#ar)" marker-end="url(#ar)"/>
        <text class="dimt" x="90" y="88" text-anchor="middle">28</text>
        <text class="small" x="112" y="20">2 × Ø10 × 8</text>
        <text class="small" x="112" y="44">S4 centré</text>
        <text class="small" x="112" y="66">B2 (extérieur)</text>
        <text class="small" x="4" y="20">avant ↑</text>
        <text class="small" x="4" y="62">arrière ↓</text>
      </svg>
      <p>Coupe juste sous le genou, vue de dessus. Les tubes sont devant, S4 derrière eux, au centre ; son palonnier
      sort côté extérieur et une entretoise amène le bras dans le plan de B2. Le raccord haut de tibia (pointillé) tient les trois.</p></div>
    <div class="sheet det wide">
      <h3>G · Ressorts de genou</h3>
      <svg viewBox="0 0 340 120" role="img" aria-label="Ressort de genou vu de côté : patte d'ancrage sur l'avant du raccord de cuisse, ressort de traction, câble Dyneema enroulé sur le profil de came de rayon 20 de la joue du tibia, tendeur M3.">
        <line class="axis" x1="20" y1="60" x2="320" y2="60"/>
        <rect class="tube" x="20" y="64" width="210" height="10"/>
        <rect class="fit" x="20" y="44" width="34" height="34" rx="2"/>
        <rect class="fit" x="40" y="34" width="10" height="12"/>
        <circle class="pin" cx="45" cy="40" r="1.8"/>
        <polyline class="spr" points="45,40 49,34 53,46 57,34 61,46 65,34 69,46 73,34 77,46 81,34 85,46 89,34 93,46 97,34 101,46 105,34 109,46 113,34 117,46 121,40"/>
        <line class="cable" x1="121" y1="40" x2="268" y2="40"/>
        <circle class="cam" cx="268" cy="60" r="20" style="stroke-dasharray:none;stroke-width:1.2"/>
        <rect class="fit" x="240" y="48" width="30" height="24" rx="3" style="fill-opacity:.4"/>
        <circle class="bearing" cx="268" cy="60" r="7"/><circle class="pin" cx="268" cy="60" r="2.4"/>
        <path class="cable" d="M268,40 A20,20 0 0 1 288,60" style="fill:none;stroke-dasharray:none;stroke-width:1.2"/>
        <circle class="pin" cx="288" cy="66" r="1.8"/>
        <line class="dim" x1="45" y1="22" x2="121" y2="22" marker-start="url(#ar)" marker-end="url(#ar)"/>
        <text class="dimt" x="83" y="18" text-anchor="middle">≈ 58 au repos</text>
        <line class="ext" x1="45" y1="25" x2="45" y2="36"/><line class="ext" x1="121" y1="25" x2="121" y2="36"/>
        <line class="dim" x1="268" y1="60" x2="268" y2="40" marker-end="url(#ar)"/>
        <text class="dimt" x="246" y="38">r 20</text>
        <text class="small" x="22" y="96">raccord haut de cuisse</text>
        <text class="small" x="22" y="103">patte + axe d'ancrage M3</text>
        <text class="small" x="78" y="56">ressort de traction (×2, côte à côte)</text>
        <text class="small" x="150" y="34">câble Dyneema Ø1</text>
        <text class="small" x="228" y="96">profil de came sur la joue</text>
        <text class="small" x="228" y="103">du tibia (×2), tendeur M3</text>
        <text class="small" x="296" y="70">fin du</text><text class="small" x="296" y="77">câble</text>
      </svg>
      <table>
        <thead><tr><th>Spécification (par ressort, 2 en parallèle)</th><th class="n">Valeur</th></tr></thead>
        <tbody>
          <tr><td>Type</td><td class="n">traction, acier ressort, crochets</td></tr>
          <tr><td>Raideur</td><td class="n">1,75 N/mm (3,5 N/mm à deux)</td></tr>
          <tr><td>Fil · Ø extérieur</td><td class="n">Ø 1,4 mm · Ø 10–11 mm</td></tr>
          <tr><td>Spires · longueur au repos</td><td class="n">≈ 29 · ≈ 58 mm crochets compris</td></tr>
          <tr><td>Allongement utile · maxi admissible</td><td class="n">35 mm · ≥ 40 mm</td></tr>
          <tr><td>Force à 35 mm</td><td class="n">≈ 61 N (contrainte ≈ 630 MPa, admissible ≈ 900)</td></tr>
          <tr><td>Couple au genou (les deux)</td><td class="n">1,4 N·m/rad au-delà de 10° : 3,7 kg·cm à 25°, 20 kg·cm à 90°</td></tr>
        </tbody>
      </table>
      <p>Les ressorts sont ancrés en haut sur un axe M3 traversant une patte du raccord de cuisse, 76 mm sous la hanche, un ressort
      au droit de chaque joue du tibia (±14,5 mm de l'axe de jambe, vue de face). En bas, un câble Dyneema s'enroule sur le profil
      de came de la joue, rayon 20 devant l'axe du genou, et se bloque sous un tendeur M3. Plier le genou déroule le câble :
      20 mm de câble par radian, soit 35 mm entre 10° et 110°. Le tendeur sert à régler l'engagement : câble juste tendu à 10°
      de flexion. Au plus plié, le bas du ressort descend à 169 mm sous la hanche, avant la chape du genou.</p>
    </div>
    <div class="sheet det wide">
      <h3>H · Attaches des bielles (a, b, c, d)</h3>
      <svg viewBox="0 0 340 112" role="img" aria-label="Empilage vu en coupe à chaque extrémité de bielle : côté servo, palonnier, entretoise, bras, rondelle, rotule à œil, rondelle, vis M3 et écrou frein ; côté articulation, levier imprimé avec insert M3.">
        <text class="lbl" x="10" y="12">Côté servo (a, c)</text>
        <rect class="servo" x="10" y="20" width="26" height="60" rx="2"/>
        <rect class="horn" x="36" y="34" width="5" height="32"/>
        <rect class="fit" x="41" y="38" width="14" height="24"/>
        <rect class="arm2" x="55" y="34" width="5" height="40"/>
        <rect class="bolt" x="60" y="64" width="1.5" height="10"/>
        <circle class="rodend" cx="66.5" cy="69" r="5"/>
        <rect class="bolt" x="71.5" y="64" width="1.5" height="10"/>
        <line class="bolt" x1="55" y1="69" x2="77.5" y2="69" style="stroke-width:2.6;stroke:var(--axis)"/>
        <rect class="bolt" x="73.5" y="65" width="4" height="8"/>
        <line class="rod" x1="66.5" y1="74" x2="66.5" y2="104" style="stroke-width:3"/>
        <text class="small" x="10" y="90">servo</text>
        <text class="small" x="30" y="104">palonnier</text>
        <text class="small" x="44" y="56">entretoise</text>
        <text class="small" x="49" y="30">bras 22</text>
        <text class="small" x="81.5" y="86">rotule à œil M3</text>
        <text class="small" x="81.5" y="93">vis M3 + écrou frein</text>
        <text class="lbl" x="200" y="12">Côté articulation (b, d)</text>
        <rect class="fit" x="200" y="20" width="12" height="62"/>
        <rect class="arm2" x="212" y="56" width="6" height="22"/>
        <rect class="bolt" x="218" y="64" width="1.5" height="10"/>
        <circle class="rodend" cx="224" cy="69" r="5"/>
        <rect class="bolt" x="229" y="64" width="1.5" height="10"/>
        <line class="bolt" x1="212" y1="69" x2="236" y2="69" style="stroke-width:2.6;stroke:var(--axis)"/>
        <rect class="bolt" x="236" y="65" width="3" height="8"/>
        <line class="rod" x1="224" y1="74" x2="224" y2="104" style="stroke-width:3"/>
        <text class="small" x="186" y="96">joue extérieure</text>
        <text class="small" x="244" y="60">levier 22 venu avec la joue,</text>
        <text class="small" x="244" y="67">insert laiton M3</text>
        <text class="small" x="244" y="76">vis M3 × 16 + frein filet</text>
        <text class="small" x="244" y="85">rondelle de chaque côté</text>
        <text class="small" x="244" y="92">de la rotule</text>
      </svg>
      <table>
        <thead><tr><th>Extrémité</th><th>Sur quoi</th><th>Empilage</th></tr></thead>
        <tbody>
          <tr><td><b>a</b> · B1 haut</td><td>bras de S3, 22 mm</td><td>palonnier S3 → entretoise 11,5 mm → bras alu ou PETG → rondelle → rotule → rondelle → vis M3 × 25 + écrou frein</td></tr>
          <tr><td><b>b</b> · B1 bas</td><td>levier du genou, sur la joue extérieure du tibia, 22 mm de l'axe</td><td>levier imprimé avec insert laiton M3 → rondelle → rotule → rondelle → vis M3 × 16 + frein filet</td></tr>
          <tr><td><b>c</b> · B2 haut</td><td>bras de S4, 22 mm</td><td>palonnier S4 → entretoise 3,5 mm → bras → rondelle → rotule → rondelle → vis M3 × 16 + écrou frein</td></tr>
          <tr><td><b>d</b> · B2 bas</td><td>levier de talon, sur la joue extérieure du pied, 22 mm derrière la cheville</td><td>levier imprimé avec insert laiton M3 → rondelle → rotule → rondelle → vis M3 × 16 + frein filet</td></tr>
        </tbody>
      </table>
      <p>Chaque bielle = tube carbone + goujon M3 collé à chaque bout + <b>rotule à œil M3 femelle</b> (embout à rotule
      métallique) vissée sur le goujon et bloquée par un contre-écrou. La vis traverse l'œil de la rotule et se serre dans
      le bras ou le levier ; les deux rondelles laissent la rotule pivoter de quelques degrés, ce qui absorbe les petits
      défauts d'alignement entre les plans. Côté servo, l'entretoise est vissée avec le bras sur le palonnier par les vis
      du palonnier : elle amène le bras dans le plan de la bielle (35 mm de l'axe de jambe pour B1, 27 mm pour B2).</p>
    </div>
    <div class="sheet det">
      <h3>F · Bilan de masse d'une jambe</h3>
      <table>
        <thead><tr><th>Sous la hanche</th><th class="n">Rév. E, 170</th><th class="n">Rév. F, 200</th></tr></thead>
        <tbody>
          <tr><td>Servos S3 + S4</td><td class="n">110 g</td><td class="n">110 g</td></tr>
          <tr><td>Raccords, chapes, roulements</td><td class="n">78 g</td><td class="n">78 g</td></tr>
          <tr><td>Tubes, bielles, ressort</td><td class="n">36 g</td><td class="n">42 g</td></tr>
          <tr><td>Pied + semelle</td><td class="n">25 g</td><td class="n">32 g</td></tr>
          <tr><td><b>Total</b></td><td class="n"><b>249 g</b></td><td class="n"><b>262 g</b></td></tr>
          <tr><td>Inertie autour de la hanche</td><td class="n">9,0 g·m²</td><td class="n warn">13,7 g·m²</td></tr>
        </tbody>
      </table>
      <p>Estimations, pied de 100 × 65 compris. Des segments plus longs ne pèsent presque rien de plus, mais éloignent le pied et S4 de la
      hanche : inertie ×1,5. Le balancement est plus lent, le pas 18 % plus long, la vitesse de marche reste proche.</p>
    </div>
  </div>
</section>

<section>
  <h2>Stabilité et pieds</h2>
  <p>Simulation de la marche avec le modèle du pendule inverse (centre de gravité à 0,50 m, 2,1 kg) et la commande
  prédictive classique des bipèdes : le point d'appui (ZMP) est visé au centre du pied pendant l'appui simple. On
  mesure la marge restante entre ce point et le bord du pied, en retirant 5 mm d'erreur de commande et la perturbation
  due à la jambe qui avance (jusqu'à 37 mm à 0,44 m/s si le contrôleur ne la compense pas, environ 30 % de ça s'il la
  compense).</p>
  <div class="tw"><table>
    <thead><tr><th>Pied</th><th class="n">Vitesse m/s</th><th>Jambe en l'air compensée</th><th class="n">Marge avant mm</th><th class="n">Marge arrière mm</th><th class="n">Marge latérale mm</th><th class="n">Poussée latérale encaissée m/s</th></tr></thead>
    <tbody>
      <tr><td>85×55 (actuel)</td><td class="n">0,22</td><td>non</td><td class="n ok">19,0</td><td class="n ok">16,9</td><td class="n ok">19,5</td><td class="n">0,09</td></tr>
      <tr><td>85×55 (actuel)</td><td class="n">0,22</td><td>oui</td><td class="n ok">31,0</td><td class="n ok">28,9</td><td class="n ok">19,5</td><td class="n">0,09</td></tr>
      <tr><td>85×55 (actuel)</td><td class="n">0,33</td><td>non</td><td class="n warn">8,7</td><td class="n warn">5,2</td><td class="n ok">18,6</td><td class="n">0,08</td></tr>
      <tr><td>85×55 (actuel)</td><td class="n">0,33</td><td>oui</td><td class="n ok">27,4</td><td class="n ok">23,9</td><td class="n ok">18,6</td><td class="n">0,08</td></tr>
      <tr><td>85×55 (actuel)</td><td class="n">0,44</td><td>non</td><td class="n bad">-3,3</td><td class="n bad">-9,0</td><td class="n ok">17,4</td><td class="n">0,08</td></tr>
      <tr><td>85×55 (actuel)</td><td class="n">0,44</td><td>oui</td><td class="n ok">22,8</td><td class="n ok">17,1</td><td class="n ok">17,4</td><td class="n">0,08</td></tr>
      <tr><td>100×65</td><td class="n">0,22</td><td>non</td><td class="n ok">26,5</td><td class="n ok">24,4</td><td class="n ok">24,5</td><td class="n">0,11</td></tr>
      <tr><td>100×65</td><td class="n">0,22</td><td>oui</td><td class="n ok">38,5</td><td class="n ok">36,4</td><td class="n ok">24,5</td><td class="n">0,11</td></tr>
      <tr><td>100×65</td><td class="n">0,33</td><td>non</td><td class="n ok">16,2</td><td class="n warn">12,7</td><td class="n ok">23,6</td><td class="n">0,1</td></tr>
      <tr><td>100×65</td><td class="n">0,33</td><td>oui</td><td class="n ok">34,9</td><td class="n ok">31,4</td><td class="n ok">23,6</td><td class="n">0,1</td></tr>
      <tr><td>100×65</td><td class="n">0,44</td><td>non</td><td class="n bad">4,2</td><td class="n bad">-1,5</td><td class="n ok">22,4</td><td class="n">0,1</td></tr>
      <tr><td>100×65</td><td class="n">0,44</td><td>oui</td><td class="n ok">30,3</td><td class="n ok">24,6</td><td class="n ok">22,4</td><td class="n">0,1</td></tr>
    </tbody>
  </table></div>
  <p><b>Lecture.</b> D'avant en arrière, le pied de 85 mm ne suffisait que si le contrôleur compense la jambe en l'air ; son talon
  de 25 mm était le point faible. Le pied de <b>100 × 65 mm</b> (talon 35, pointe 65) garde au moins 12 mm de marge
  jusqu'à 0,33 m/s même sans compensation, et 25 mm à 0,44 m/s avec. Sur le côté, la marge plafonne autour de 22 mm
  quelle que soit la vitesse : sans roulis de cheville, seule la largeur du pied tient le robot, et une poussée latérale de
  plus de 0,1 m/s ne se rattrape pas sur place. Elle se rattrape par un pas de côté (le roulis de hanche de +30° place le
  pied jusqu'à environ 22 cm), par les propulseurs, ou en V2 avec le roulis de cheville.</p>
  <p>Plus large que 65 mm, les pieds se rapprocheraient à moins de 25 mm l'un de l'autre : risque d'accrocher le pied
  d'appui en marchant. Plus long que 100 mm, le pied pèse plus au bout de la jambe sans gain utile sous 0,45 m/s.</p>
  <div class="sheet topwrap">
    <svg viewBox="__TOPVB__" role="img" aria-label="Vue de dessus : six pas à 0,33 m/s avec des pieds de 100 × 65 mm ; le centre de gravité oscille d'environ 21 mm de chaque côté, le point d'appui reste au centre de chaque pied.">
      __TOP__
    </svg>
  </div>
  <div class="legend">
    <span><i class="sw petg"></i>empreinte d'un pied 100 × 65 (point = axe de cheville)</span>
    <span><i class="sw com"></i>centre de gravité</span>
    <span><i class="sw zmp"></i>point d'appui (ZMP)</span>
    <span>Vue de dessus, marche simulée à 0,33 m/s (pas de 130 mm, 0,4 s par pas), cotes en mm.</span>
  </div>
</section>

<section>
  <h2>Points limites et correctifs</h2>
  <div class="tw"><table>
    <thead><tr><th>Point limite</th><th class="n">Avant</th><th>Correctif</th><th class="n">Après</th></tr></thead>
    <tbody>
      <tr><td>Genou en marche, flexion 25–30°</td><td class="n warn">11,3–13,5</td><td>Ressort de genou engagé dès 10° (≈ 1,4 N·m/rad) et marche à 20–25° de flexion</td><td class="n ok">7,6–8,5</td></tr>
      <tr><td>Genou à 40° et plus</td><td class="n bad">17,8</td><td>Hors de la plage de marche ; le ressort porte l'accroupi</td><td class="n ok">évité</td></tr>
      <tr><td>Genou accroupi à 90° (2 jambes)</td><td class="n warn">14</td><td>Le ressort donne ≈ 20 kg·cm à 90°</td><td class="n ok">≈ 0</td></tr>
      <tr><td>Genou, impulsion de saut</td><td class="n bad">35</td><td>Ressort 20 + servo en pointe (bref) + poussée 1,3 × poids</td><td class="n ok">couvert</td></tr>
      <tr><td>Genou en l'air (jambe qui avance, 45°)</td><td class="n">≈ 2</td><td>Coût du ressort : le servo plie la jambe contre lui</td><td class="n warn">≈ 8,7</td></tr>
      <tr><td>Hanche roulis, transfert de poids</td><td class="n warn">12</td><td>Hanches à 90 mm et buste décalé au-dessus du pied d'appui avant de lever l'autre</td><td class="n ok">4–6, pic 9</td></tr>
      <tr><td>Cheville, poussée sur la pointe</td><td class="n warn">10</td><td>Pas de poussée de pointe : centre de pression gardé à ±30 mm de l'axe</td><td class="n ok">≈ 6</td></tr>
    </tbody>
  </table></div>
  <p>Valeurs en kg·cm, robot de 2,0 kg sur une jambe, chocs ×1,3. Repère STS3215 : 30 kg·cm en blocage, environ 10 en
  continu. Ressort de genou : 2 ressorts de traction de 1,75 N/mm en parallèle sur la came de rayon 20, course utile 35 mm,
  force maxi environ 61 N chacun. Si le genou chauffe malgré tout en marche, la solution de repli est un STS3250 aux deux
  genoux seulement.</p>
  <p class="note">Changement par rapport à ma proposition précédente : la bielle « 20/26 » qui donnait ×1,3 au genou ne
  tient pas sur toute la course. Le calcul de la bielle montre qu'aucune géométrie à 4 barres ne donne plus de ×1,1 tout en
  couvrant 0–110° avec un angle de transmission correct. On garde donc le parallélogramme 22/22 (angle de transmission
  ≥ 35° de 0 à 110°), et c'est le ressort engagé plus tôt qui soulage le genou.</p>
</section>

<section>
  <h2>Cotes d'interface et impression</h2>
  <div class="tw"><table>
    <thead><tr><th>Interface</th><th class="n">Cote nominale</th><th class="n">À dessiner (PETG, FDM)</th></tr></thead>
    <tbody>
      <tr><td>Logement roulement 625ZZ</td><td class="n">Ø16 × 5</td><td class="n">Ø16,15 × 5, épaulement Ø13</td></tr>
      <tr><td>Vis épaulée M5 dans la pièce fixe</td><td class="n">Ø5</td><td class="n">Ø5,2 (passage)</td></tr>
      <tr><td>Emmanchement tube Ø12 · Ø10</td><td class="n">20 mm</td><td class="n">Ø12,2 · Ø10,2 × 20, fente 1,5 + collier M3</td></tr>
      <tr><td>Poche de servo</td><td class="n">45,2 × 24,7 × 35</td><td class="n">+0,2 par côté</td></tr>
      <tr><td>Insert laiton M3</td><td class="n">—</td><td class="n">Ø4,0 × 5,7 (selon l'insert)</td></tr>
      <tr><td>Passage vis M3 · M2</td><td class="n">—</td><td class="n">Ø3,3 · Ø2,3</td></tr>
      <tr><td>Moyeu arrière du servo</td><td class="n">Ø6</td><td class="n">alésage Ø6,2, appui sur rondelle M3</td></tr>
      <tr><td>Axe de rotule (bras, levier)</td><td class="n">M3</td><td class="n">insert M3, ou écrou frein derrière</td></tr>
    </tbody>
  </table></div>
  <p><b>Impression :</b> PETG, 4 parois, 5 couches dessus et dessous, remplissage gyroïde 40 % (60 % pour les raccords
  du genou et la chape en U). Imprime les pièces qui portent un roulement avec l'axe vertical, pour que les logements
  sortent ronds. Fais un test d'emmanchement (un anneau Ø16,15 et un manchon Ø12,2) avant les grosses pièces : chaque
  imprimante a son propre jeu.</p>
</section>

<section>
  <h2>Visserie d'une jambe</h2>
  <div class="tw"><table>
    <thead><tr><th>Pièce</th><th class="n">Qté</th><th>Où</th></tr></thead>
    <tbody>
      <tr><td>Vis M2 (longueur selon ton servo) </td><td class="n">16</td><td>berceaux des 4 servos</td></tr>
      <tr><td>Vis de palonnier (fournies) + vis du palonnier vers la pièce</td><td class="n">4 + 16</td><td>S1 à S4</td></tr>
      <tr><td>Vis M3 × 8 + rondelle M3</td><td class="n">2</td><td>moyeux arrière de S1 et S2</td></tr>
      <tr><td>Roulement 625ZZ</td><td class="n">4</td><td>genou, cheville</td></tr>
      <tr><td>Vis épaulée M5 + écrou frein + 2 rondelles</td><td class="n">2</td><td>genou, cheville</td></tr>
      <tr><td>Rotule à œil M3 métal + goujon M3 collé + contre-écrou</td><td class="n">4</td><td>bielles B1 et B2</td></tr>
      <tr><td>Vis M3 × 16 / × 25 + 2 rondelles</td><td class="n">3 + 1</td><td>attaches b, c, d / a</td></tr>
      <tr><td>Vis M3 × 12 + écrou (colliers de tubes)</td><td class="n">6</td><td>cuisse ×2, tibia ×4</td></tr>
      <tr><td>Axe M3 × 45 + écrou frein · tendeur M3 × 8</td><td class="n">1 · 2</td><td>ressorts de genou</td></tr>
      <tr><td>Vis M3 × 10 + insert laiton</td><td class="n">4</td><td>berceau de S1 sur la plaque de bassin</td></tr>
      <tr><td>Inserts laiton M3</td><td class="n">≈ 12</td><td>leviers, berceaux, plaque</td></tr>
    </tbody>
  </table></div>
  <p>Avec le moyeu arrière des servos, la hanche n'a plus besoin de roulement ni de vis épaulée : 4 roulements par
  jambe au lieu de 6 (environ −9 g).</p>
</section>

<section>
  <h2>À vérifier avant d'imprimer</h2>
  <p>Le boîtier du STS3215 est dessiné à 45,2 × 24,7 mm avec l'arbre à 11 mm d'un bout : mesure ton servo et ajuste
  les poches. Vérifie aussi le diamètre des trous taraudés du boîtier et des vis du palonnier, la longueur réelle de tes
  rotules (le 16 mm des bielles), et le diamètre intérieur de tes tubes carbone avant de dessiner les emmanchements.</p>
</section>
</div>
'''
html = (html.replace("__SERVO__", hip.servo_svg).replace("__SVB__", hip.SERVO_VB)
        .replace("__HSIDE__", hip.hip_side_svg).replace("__HSVB__", hip.HIP_SIDE_VB)
        .replace("__HFRONT__", hip.hip_front_svg).replace("__HFVB__", hip.HIP_FRONT_VB)
        .replace("__TOP__", top.top_svg).replace("__TOPVB__", top.VB)
        .replace("__SIDE__", leg.side_svg).replace("__FRONT__", front.front_svg.replace("url(#ar)", "url(#ar2)"))
        .replace("__FRONTH__", str(front.GY + 168))
        .replace("__SIDEH__", str(round(G + 36 + 112)))
        .replace("__TV__", str(D["thigh_vis"])).replace("__TC__", str(D["thigh_cut"]))
        .replace("__SV__", str(D["shank_vis"])).replace("__SC__", str(D["shank_cut"]))
        .replace("__B1C__", str(D["B1_cut"])).replace("__B2C__", str(D["B2_cut"]))
        .replace("__B1__", str(D["B1"])).replace("__B2__", str(D["B2"])))
open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'jambe_leo_s.html'), 'w').write(html)
print("ok", len(html))
