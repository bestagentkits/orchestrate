# Maintaining the docs

This document was moved out of `README.md`. That file is a published reader surface and
a parity-checked summary of `plugins/orchestrate/skills/orchestrate/references/`, so
maintainer material belongs under `docs/` — the convention `AGENTS.md` states. The move
changed the location of the sweep, not the mechanism, and it is guarded by step 19
below so the pointer cannot dangle again.

This repository ships no code and no `package.json`, so there is no committed
linter: a doc-integrity script would be its first executable, would sit outside
the published plugin payload, and would contradict the rule in
`dispatch-hardening.md` that bundled scripts resolve skill-relative rather than
from the repo root. Containment here is therefore **normative, not mechanical** —
and this document exists so that any maintainer can *re-run* it rather than trust
it.

The one workflow under `.github/workflows/` publishes `site/` to GitHub Pages. It
runs no check and gates nothing: a documentation change is still verified by the
sweep below, by a maintainer.

Run the whole sweep before merging a change to this reference set. **Run it from the
repository root**: every path below is repository-root-relative, and this document's
own location is not its working directory. Every command below is copy-pasteable, and
the controls in step 2 verify that the checks themselves work.

The flow figure on the landing page is a **compiled copy**. Its sources are
`site/flow/routing.json` and `site/flow/review.json`, typed diagram IR in the format the
`ak:diagram` skill consumes; each is compiled with
`node scripts/compiler/compile.mjs --input <ir> --format svg --preset editorial --theme light`
and the result is inlined with its `aria-label` replaced by `aria-labelledby`. The
repository carries no compiler, so the sweep asserts the panels' declared envelope against
the IR and not their geometry: a changed IR that is not recompiled is caught, a correct
recompilation is not re-derived.

Two limits are worth stating before anyone trusts a green run. The **no copied measurement**
rule — that no benchmark value, model name, flag or leaderboard row is pasted into the
skill — is a **review item a grep cannot enforce**, because any token check would have to
name the token it forbids. And a grep proves a token *exists*, not that a rule *holds*: a
passing sweep is not evidence that no benchmark value was copied, only that the checks
below found nothing.

```bash
# 1. DENYLIST — no link to a deleted reference, and not to the old Pi location.
#    The alternation lives in a variable so this block cannot match itself.
refs='model-routing|runtime-matrix|harness-profiles|arbiter-checklist|pi-sessions'
grep -rnE "\]\([^)]*($refs)\.md\)" --include='*.md' . | grep -v '^\./plans/'
grep -rnE "\]\([^)]*references/pi-onboarding\.md\)" --include='*.md' . | grep -v '^\./plans/'
#    Both must print nothing.

# 2. CONTROLS — prove the denylist can catch a stale link and does not misfire.
#    The probe is assembled from parts so this block cannot match itself.
printf 'x [a](references/%s.md)\n' 'model-routing' > /tmp/stale.md
grep -qE "\]\([^)]*($refs)\.md\)" /tmp/stale.md && echo "control OK: stale caught" || echo "CONTROL FAILED"
printf 'x [a](runtimes/pi-%s.md)\n' 'onboarding' > /tmp/valid.md
grep -qE "\]\([^)]*references/pi-onboarding\.md\)" /tmp/valid.md && echo "CONTROL FAILED: valid flagged" || echo "control OK: valid relocated path not flagged"
rm -f /tmp/stale.md /tmp/valid.md

# 3. VERSION — exact surface counts, not merely "present", and no replaced version
#    left behind. 2.1.0 is the version this release replaces, so it is denied too.
test "$(grep -c '2\.2\.0' plugins/orchestrate/.claude-plugin/plugin.json)" = 1 || echo "FAIL plugin.json"
test "$(grep -c '2\.2\.0' plugins/orchestrate/skills/orchestrate/SKILL.md)" = 1 || echo "FAIL SKILL.md"
test "$(grep -c '2\.2\.0' site/index.html)" = 3 || echo "FAIL site (byline, spec table, vi i18n byline)"
#    AGENTS.md is a reader surface this release created, so it is swept too.
#    README.md is exempt: it keeps the historical upgrade sections, which name
#    1.8.x, 2.0.0, 2.0.1, 2.1.0 and 2.2.0 by design.
grep -rn '2\.0\.0\|2\.0\.1\|2\.1\.0\|1\.8\.0' plugins site .claude-plugin AGENTS.md \
  --include='*.json' --include='*.md' --include='*.html' && echo "FAIL stale version" || echo "version clean"

# 4. REACHABILITY — every reference and adapter note is linked by a peer,
#    whether the link is bare or path-qualified. A file must not count itself.
for f in plugins/orchestrate/skills/orchestrate/references/*.md \
         plugins/orchestrate/skills/orchestrate/runtimes/*.md; do
  b=$(basename "$f")
  grep -rqE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" \
    plugins/orchestrate/skills/orchestrate README.md || echo "UNREACHABLE $b"
done

# 5. BOUNDARY — the accept predicate has exactly one owner, and a second owner must
#    fail rather than merely print an extra line a human might not read.
test "$(grep -rl 'Accept without a C3 call' plugins/orchestrate/skills/orchestrate/references | wc -l)" = 1 \
  || echo "FAIL: the accept predicate has more than one owner"
test "$(grep -rl 'Accept without a C3 call' plugins/orchestrate/skills/orchestrate/references)" \
  = plugins/orchestrate/skills/orchestrate/references/verification.md \
  || echo "FAIL: the accept predicate is not owned by verification.md"
#    Must print nothing.

# 6. PARITY — reader-facing surfaces must not state a weaker control for ANY tier.
#    These clauses must survive every summary, per tier.
check() { grep -qF "$2" "$1" || echo "PARITY FAIL $1 missing: $2"; }
for f in README.md site/index.html; do
  check "$f" "no unnecessary write or shell grant"   # R0
  check "$f" "no permission bypass"                  # R1
  check "$f" "explicit checks and arbiter review"    # R2
  check "$f" "strongest verified controls"           # R3
done
#    Must print nothing.

# 7. STUBS — unverified adapters stay unmistakably non-normative.
#    A loop rather than `grep -L`, whose exit status is not a pass/fail signal:
#    GNU grep returns 0 when files are listed, so a wrapper would read the opposite
#
#    result. The loop fails loudly on a missing banner instead.
for f in plugins/orchestrate/skills/orchestrate/runtimes/{claude,codex,gemini,opencode,aider}.md; do
  grep -q 'Status: unverified — not a support claim, not in inventory' "$f" \
    || echo "STUB FAIL $f"
done
#    Must print nothing.

# 8. SITE I18N — every data-i18n key in the markup has a Vietnamese entry, so a
#    new section cannot ship as English-only. The control proves the check fails.
for k in $(grep -o 'data-i18n="[^"]*"' site/index.html | cut -d'"' -f2 | sort -u); do
  grep -qE "(^|[ ,{]) *$k:" site/index.html || echo "I18N FAIL no VI entry: $k"
done
grep -qE '(^|[ ,{]) *noSuchKey:' site/index.html && echo "CONTROL FAILED" || echo "control OK: absent key detected"

# --- Steps added by 2.2.0 -------------------------------------------------
S=plugins/orchestrate/skills/orchestrate/references

# 9. NEW REFERENCES — each exists AND is reachable from a PEER document, not only
#    from SKILL.md's index row. The index row alone survives a broken cross-reference.
for b in harness-portability.md benchmark-evidence.md fallback-policy.md trace-and-logging.md; do
  test -f "$S/$b" || echo "MISSING $b"
  grep -rqE "\]\([^)]*/?$b\)" --include='*.md' --exclude="$b" --exclude='SKILL.md' \
    plugins/orchestrate/skills/orchestrate README.md || echo "NO PEER LINK for $b"
done
#    Must print nothing. SKILL.md is excluded above: its index row alone satisfies the
#    search, and an index row surviving a broken cross-reference is the one failure
#    this check exists to catch.

# 10. PORTABILITY — the payload may never depend on a Claude-Code-only feature, and
#     the one document REQUIRED to name them is excluded from the sweep.
#     --exclude, not `grep -v`: a `grep -v` on path:line output also drops any line
#     whose CONTENT names the excluded file, so a real violation annotated
#     "see harness-portability.md" would have read as clean.
grep -rn --exclude='harness-portability.md' 'context: fork\|^hooks:\|^allowed-tools:' \
  plugins/orchestrate/skills/orchestrate || echo "portability clean"
for f in "$S/harness-portability.md" README.md site/index.html; do
  grep -q 'npx skills add bestagentkits/orchestrate' "$f" || echo "CLI PATH MISSING in $f"
done

# 11. NEGATIVE SAFETY RULES — the two rules the release adds must be findable in
#     the file that owns each.
grep -q 'may not set eligibility' "$S/routing-policy.md" || echo "FAIL: benchmarks may gate"
grep -q 'failed check never promotes' "$S/fallback-policy.md" || echo "FAIL: check may promote"
grep -q 'authorization or permission failure never promotes' "$S/fallback-policy.md" || echo "FAIL: permission may promote"
#    The reader surfaces state both rules too, and most readers meet them there first.
grep -q 'cannot set eligibility, a floor, a tier, a control or an approval' README.md \
  || echo "FAIL: benchmark-never-gates rule missing from README"
grep -q 'failed check never promotes' README.md \
  || echo "FAIL: check-may-promote rule missing from README"
#    Must print nothing.

# 12. CREDENTIALS — the four paths live in one owner, in order, and nowhere else;
#     dotenv files stay untracked.
#    Anchored to the ordered list, so prose that also mentions a location cannot
#    inflate the count: only the four numbered locations are compared.
paths=$(grep -nE '^[0-9]+\. (the process environment|the project `\.env`|the `skills/` directory|the skill.s own `\.env`)' "$S/decision-plane.md")
test "$(printf '%s\n' "$paths" | wc -l)" = 4 || echo "FAIL: the credential order is not four locations"
#    Order, asserted by the numbering: location N must be the Nth documented location.
test "$(grep -cE '^1\. the process environment' "$S/decision-plane.md")" = 1 \
  || echo "FAIL: credential location 1 is not the process environment"
test "$(grep -cE '^2\. the project `\.env`' "$S/decision-plane.md")" = 1 \
  || echo "FAIL: credential location 2 is not the project .env"
test "$(grep -cE '^3\. the `skills/` directory' "$S/decision-plane.md")" = 1 \
  || echo "FAIL: credential location 3 is not the skills directory"
test "$(grep -cE '^4\. the skill.s own' "$S/decision-plane.md")" = 1 \
  || echo "FAIL: credential location 4 is not the skill's own .env"
echo -n "duplicated order (must be 1 file): "; grep -rl 'process\.env' "$S" | wc -l
git check-ignore -q .env && echo ".env ignored" || echo "FAIL: .env not ignored"
#    Any dotenv except the template. The rule cannot simply forbid `.env.*`, because
#    `.gitignore` exempts `.env.example` on purpose, so the pattern has to let the
#    template through while still catching `.env.local`. `wc -l` rather than `grep -c`,
#    so that an empty result counts 0 instead of one empty line.
bad=$(git ls-files | grep -E '(^|/)\.env' | grep -vE '(^|/)\.env\.example$' | wc -l)
test "$bad" = 0 || echo "FAIL: dotenv tracked"
#    The template is the one dotenv meant to be tracked, and it must stay valueless:
#    a real key pasted into the example is this file's characteristic failure, and it
#    is the one place a key could be committed without touching an ignored path.
test "$(git ls-files | grep -cE '(^|/)\.env\.example$')" = 1 \
  || echo "FAIL: .env.example is not tracked"
test "$(grep -vE '^[[:space:]]*(#|$)' .env.example | grep -vE '=[[:space:]]*$' | wc -l)" = 0 \
  || echo "FAIL: .env.example carries a value"
#    The pattern is assembled from parts so this block cannot match itself. `docs`
#    joined the scan set when the sweep moved there: a reader surface that hosts the
#    guard must itself be guarded.
keypat='echo .*TYPESAFE''_API_KEY'
envpat='cat .*[.]env'
grep -rn "$keypat\|$envpat" plugins README.md site AGENTS.md CLAUDE.md docs 2>/dev/null \
  || echo "no key-printing guidance"

# 13. TRACE — the span identifiers live in the new document AND in their owners.
grep -q 'spanId' "$S/trace-and-logging.md" || echo "FAIL: span not owned"
grep -q 'spanId' "$S/event-protocol.md" || echo "FAIL: envelope missing span"
grep -q 'spanId' "$S/decision-plane.md" || echo "FAIL: decision trace missing span"
test "$(grep -c 'attemptId' "$S/trace-and-logging.md")" = 0 || echo "FAIL: invented attempt spelling"
grep -q 'trace.jsonl' "$S/output-layout.md" && echo "trace artifact listed"
grep -q 'traceStatus' "$S/output-layout.md" && echo "completeness field defined"

# 14. LANDING PAGE — the invariants that can actually fail. Everything is asserted
#     against the NEW artifacts, because the blanket reduced-motion rule and the two
#     pre-existing aria-labels would make weaker checks pass at baseline.
test "$(grep -c '<svg' site/index.html)" -ge 1 || echo "FAIL: no inline svg"
test "$(grep -c '@keyframes' site/index.html)" -ge 1 || echo "FAIL: no animation"
grep -q 'aria-labelledby="flowCaption"' site/index.html || echo "FAIL: svg has no accessible name"
test "$(grep -c 'data-i18n="flowCaption"' site/index.html)" = 1 || echo "FAIL: caption key count"
#     Both panels are compiler output, not hand-drawn: assert the emitter's hooks, and
#     that its finite motion is preference-gated rather than merely present.
test "$(grep -c 'class="ak-diagram-svg flow"' site/index.html)" = 2 || echo "FAIL: diagram panels"
test "$(grep -cE '<svg[^>]*data-animation="trace"' site/index.html)" = 2 \
  || echo "FAIL: finite motion"   # the attribute also opens a rule in the emitter's CSS
grep -q 'prefers-reduced-motion: no-preference' site/index.html \
  || echo "FAIL: diagram motion is not preference-gated"
#     The embedded SVG carries its own guard, so it stays safe when lifted out of this
#     page; this page's blanket rule alone would not survive that extraction.
grep -q '.ak-diagram-svg \*, .ak-diagram-svg { animation: none !important; transition: none !important; }' \
  site/index.html || echo "FAIL: no self-contained reduced-motion guard"
#     Node families must be exactly the set the stylesheet re-clothes. A family the IR
#     gains later renders in the compiler's own hue, which nothing else here sees.
python3 - <<'PY2' || echo "FAIL: node family set"
import re, pathlib, sys
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
i = s.index('<section id="flow"'); s = s[i:s.index('</section>', i)]
have = set(re.findall(r'<g class="ak-node"[^>]*data-family="([^"]+)"', s))
want = {"process", "service", "decision", "start", "success", "failure", "waiting"}
if have - want:
    print("UNMAPPED FAMILY", sorted(have - want)); sys.exit(1)
if want - have:
    print("MAPPED FAMILY UNUSED", sorted(want - have)); sys.exit(1)
PY2
#     The panels ship no edge labels on purpose: the compiler centres a label on its
#     edge and emits node cards afterwards, so any label whose box meets a card is
#     partly painted over — seven of twelve did. Assert the property that forced that
#     choice rather than the choice itself, so adding a label back is checked.
python3 - <<'PY3' || echo "FAIL: edge label occluded"
import re, pathlib, sys
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
i = s.index('<section id="flow"'); sec = s[i:s.index('</section>', i)]
bad = []
for panel in sec.split('<svg class="ak-diagram-svg flow"')[1:]:
    panel = panel[:panel.index('</svg>')]
    rect = r'<rect class="ak-%s" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"'
    cards = [tuple(map(float, m)) for m in re.findall(rect % 'node-card', panel)]
    masks = [tuple(map(float, m)) for m in re.findall(rect % 'edge-label-mask', panel)]
    for mx, my, mw, mh in masks:
        for cx, cy, cw, ch in cards:
            if mx < cx + cw and mx + mw > cx and my < cy + ch and my + mh > cy:
                bad.append((mx, my))
if bad:
    print("OCCLUDED LABEL at", bad); sys.exit(1)
PY3
#     The declaration that hides an edge until it draws is only safe because the
#     emitter puts it inside the no-preference block. Move it out and every reduced-
#     motion reader gets a diagram with no edges at all — which no other check sees.
python3 - <<'PY4' || echo "FAIL: edge-hiding rule is not preference-gated"
import re, pathlib, sys
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
i = s.index('<section id="flow"'); sec = s[i:s.index('</section>', i)]
def gated(text, needle):
    for m in re.finditer(r'@media[^{]*prefers-reduced-motion:\s*no-preference[^{]*\{', text):
        j = m.end(); depth = 1
        while depth and j < len(text):
            if text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        if needle in text[m.end():j]:
            return True
    return False
bad = []
for n, panel in enumerate(sec.split('<svg class="ak-diagram-svg flow"')[1:]):
    panel = panel[:panel.index('</svg>')]
    #     Exactly one occurrence, and it is the gated one: a second copy outside the
    #     block would hide edges for everyone, and losing it entirely is a change of
    #     rendering behaviour worth a look.
    if panel.count('stroke-dashoffset: 100') != 1 or not gated(panel, 'stroke-dashoffset: 100'):
        bad.append((n, panel.count('stroke-dashoffset: 100')))
if bad:
    print("EDGE HIDING NOT PREFERENCE-GATED", bad); sys.exit(1)
PY4
#     The emitter runs its flow pass three times and stops, which leaves both panels
#     static after about five seconds. The page loops it — and the gate is load
#     bearing, because the emitter's own reduced-motion guard is `animation: none
#     !important` and an unguarded loop declared after it would out-specify it.
python3 - <<'PY5' || echo "FAIL: flow pass is not looped under the gate"
import re, pathlib, sys
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
occ = s.count('animation-iteration-count: infinite')
def gated(text, needle):
    for m in re.finditer(r'@media[^{]*prefers-reduced-motion:\s*no-preference[^{]*\{', text):
        j = m.end(); depth = 1
        while depth and j < len(text):
            if text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        if needle in text[m.end():j]:
            return True
    return False
#     Scanned document-wide: the loop rule lives in the page's own stylesheet in
#     <head>, not inside the section, unlike the inlined SVG rules above.
if occ != 1 or not gated(s, 'animation-iteration-count: infinite'):
    print("FLOW LOOP not exactly one gated declaration:", occ); sys.exit(1)
PY5
#     The compiled panels are copies of a source. Their envelope is asserted against
#     the committed IR so a drifted source is caught; the geometry is not, because
#     regenerating it needs the diagram compiler, which this repository does not carry.
python3 - <<'PY6' || echo "FAIL: IR does not match the shipped panels"
import json, re, pathlib, sys
s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
i = s.index('<section id="flow"'); sec = s[i:s.index('</section>', i)]
panels = [p[:p.index('</svg>')] for p in sec.split('<svg class="ak-diagram-svg flow"')[1:]]
files = ["site/flow/routing.json", "site/flow/review.json"]
if len(panels) != len(files):
    print("PANEL/IR COUNT", len(panels), len(files)); sys.exit(1)
bad = []
for panel, f in zip(panels, files):
    ir = json.loads(pathlib.Path(f).read_text())
    for attr, want in (("data-diagram-type", ir["diagram_type"]),
                       ("data-preset", ir["meta"]["visual_preset"]),
                       ("data-theme", ir["meta"]["theme"])):
        got = re.search(attr + r'="([^"]+)"', panel)
        if not got or got.group(1) != want:
            bad.append((f, attr, want, got.group(1) if got else None))
    if f'data-animation="{ir["meta"]["animation"]}"' not in panel:
        bad.append((f, "data-animation", ir["meta"]["animation"], None))
if bad:
    print("IR/SVG MISMATCH", bad); sys.exit(1)
PY6
nums=$(grep -o '<span class="sec-num">[0-9]*</span>' site/index.html | grep -o '[0-9]*')
test "$(printf '%s\n' "$nums" | sort -u | wc -l)" = "$(printf '%s\n' "$nums" | wc -l)" \
  || echo "FAIL: duplicate sec-num"
test "$(printf '%s\n' "$nums" | wc -l)" = 10 || echo "FAIL: sec-num sequence length"
#    Sequence, not merely length: 01..10 in order.
test "$(printf '%s\n' "$nums" | tr '\n' ' ')" = "01 02 03 04 05 06 07 08 09 10 " \
  || echo "FAIL: sec-num is not the sequence 01..10"
#    The page ships an inline <script>, so a remote script src is the most likely
#    external request and must be in the pattern.
grep -nE '<img[^>]+src="https?:|<link[^>]+href="https?:|<script[^>]+src="https?:|url\(https?:|@import[^;]*https?:|fetch\(|srcset=|@font-face|<iframe|poster="https?:|xlink:href="https?:' site/index.html \
  || echo "no external requests"

# 15. CONSTANTS — each owner-fixed bound is fanned out to its readers.
for f in "$S/benchmark-evidence.md" "$S/job-spec.md" README.md; do
  grep -q 'CACHE_TTL_MAX_HOURS' "$f" || echo "CONSTANT FAIL CACHE_TTL_MAX_HOURS in $f"
done
for f in "$S/fallback-policy.md" "$S/job-spec.md" README.md; do
  grep -q 'MAX_PROMOTIONS_MAX' "$f" || echo "CONSTANT FAIL MAX_PROMOTIONS_MAX in $f"
done
#    Presence is not enough: the values must agree, so a bound edited in one place and
#    not in the others fails here. The numbers are extracted and compared rather than
#    named, because a literal in this block would match README.md itself.
owner_ttl=$(grep -oE 'CACHE_TTL_MAX_HOURS` \| `[0-9]+' "$S/benchmark-evidence.md" | grep -oE '[0-9]+$')
readme_ttl=$(grep -oE 'CACHE_TTL_MAX_HOURS` = [0-9]+' README.md | grep -oE '[0-9]+$')
test -n "$owner_ttl" && test "$owner_ttl" = "$readme_ttl" \
  || echo "CONSTANT FAIL CACHE_TTL_MAX_HOURS value disagrees"
owner_prom=$(grep -oE 'MAX_PROMOTIONS_MAX` \| `[0-9]+' "$S/fallback-policy.md" | grep -oE '[0-9]+$')
readme_prom=$(grep -oE 'MAX_PROMOTIONS_MAX` = [0-9]+' README.md | grep -oE '[0-9]+$')
test -n "$owner_prom" && test "$owner_prom" = "$readme_prom" \
  || echo "CONSTANT FAIL MAX_PROMOTIONS value disagrees"
#    Must print nothing.

# 16. BRANDING — neither reader surface may brand itself for a single harness again.
#     The pattern is assembled from parts and the comment above avoids the phrase,
#     so this block cannot match itself.
brand="Claude"" Code Skill"
grep -n "$brand" README.md site/index.html .claude-plugin/marketplace.json \
  && echo "FAIL: claude-only branding" || echo "branding clean"
#    marketplace.json is one of the two surfaces that was actually wrong before, so it
#    is inside the sweep rather than beside it. The pattern is assembled from parts
#    because this block is itself a greppable surface of README.md.
forbrand="for Claude"" Code"
grep -n "$forbrand" README.md site/index.html .claude-plugin/marketplace.json \
  && echo "FAIL: harness branding" || echo "harness-neutral"

# 17. TREES — the normative run-directory tree and its two published copies must agree.
#     A fence-anchored check could never pass (the copies are introduced by different
#     text and one is HTML), and a whole-file search matches this block's own NORM list,
#     so each tree is read from its OWN region and the three file lists are compared.
python3 - <<'PY' || echo "FAIL: tree drift"
import pathlib, re, sys
NORM = ["jobs.yaml", "state.json", "metrics.jsonl", "runtimes.json", "decisions.jsonl",
        "calibration.json", "trace.jsonl", "report.md", "worktrees/", "graph.json", "events.jsonl"]
#    Built from parts: a literal fence here would truncate any extraction of this block
#    that scans for a closing fence, which is how the sweep itself is read.
FENCE = "`" * 3

def readme_tree():
    s = pathlib.Path("README.md").read_text(encoding="utf-8")
    return re.search(FENCE + r'text\n(.*?)' + FENCE, s[s.index("### Output layout"):], re.S).group(1)

def site_tree():
    s = pathlib.Path("site/index.html").read_text(encoding="utf-8")
    return re.search(r'<pre>(.*?)</pre>', s[s.index('data-i18n="figOut"'):], re.S).group(1)

bad = False
for name, text in (("README.md", readme_tree()), ("site/index.html", site_tree())):
    missing = [f for f in NORM if f not in text]
    if missing:
        print(f"TREE DRIFT {name} missing: {missing}"); bad = True
owner = pathlib.Path("plugins/orchestrate/skills/orchestrate/references/output-layout.md").read_text(encoding="utf-8")
#    The owner is checked in its TREE region too, not file-wide: `trace.jsonl` also
#    appears in prose, so a file-wide search stays green after the tree line is deleted.
missing = [f for f in NORM if f not in re.search(FENCE + r'text\n(.*?)' + FENCE, owner, re.S).group(1)]
if missing:
    print(f"OWNER DRIFT output-layout.md tree missing: {missing}"); bad = True
sys.exit(1 if bad else 0)
PY

# 18. LOCAL INSTALL OUTPUT — a duplicated payload must never be committable.
#     These appear in the working tree after any install-path check, and `git add -A`
#     would commit a stale copy of every owner document.
for p in .agents .claude .pi skills-lock.json; do
  test -e "$p" && { git check-ignore -q "$p" || echo "FAIL: $p is not ignored"; }
done
#    Must print nothing.

# --- Step added by the Jev reader-surface change --------------------------

# 19. THE MOVE — the sweep's own pointer must resolve, and no surface may still say
#     the sweep lives in README.md. This exists because the relocation is a contract
#     edit, not a copy edit: AGENTS.md calls this sweep the way a change here is
#     verified, so a dangling pointer leaves the repository describing a check that
#     is not where it says it is. The anchor is assembled from parts, and the document
#     that legitimately owns the phrase is excluded by path, so this block cannot
#     match itself.
anchor='Maintaining'' the docs'
test -f docs/maintaining-the-docs.md || echo "FAIL: the sweep is not where README says"
grep -q '](docs/maintaining-the-docs.md)' README.md || echo "FAIL: README does not link the sweep"
stale=$(grep -rn "$anchor" --include='*.md' --include='*.yml' . \
  | grep -v '^\./plans/' | grep -v '^\./docs/maintaining-the-docs\.md:' | wc -l)
test "$stale" = 0 || echo "FAIL: a surface still points README at the sweep"
#    Must print nothing.
```

**What these assertions do not do.** They prove that a sentence exists, a link
resolves, and a token is absent. They do **not** prove that R2 escalates, that a
calibration record is genuine, or that the decision plane holds no authority.
Those are semantic properties, and a grep cannot enforce a semantic rule. No
document in this set claims otherwise, and the two review passes that produced
this release found both of its Critical defects in exactly that gap — prose that
read correctly but meant the wrong thing. Treat the sweep as a regression net,
not as proof.

