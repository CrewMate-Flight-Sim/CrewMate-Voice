"""Converts an aircraft grammar from numeric DISCRETE_COMMANDS ids to command names (the A350 Phase 1 change).

Reads the id -> name table from that aircraft's old CommandDispatcher.cs (the `DiscreteNames` dictionary), rewrites
every out.pid="N" in <rule id="DISCRETE_COMMANDS"> to out.pid="<name>", and moves items whose name has no handler in
the app's DISCRETE_COMMAND_MAP (or discreteCommandMap) into a new CHECKLIST_RESPONSES rule (routed as DISCRETE_COMMANDS, so the JSON is
unchanged). It asserts that every phrase keeps its old name and that no other rule changed.

Usage (from the aircraft repo root, before deleting CopilotSpeechNew/):
  python <voice repo>/Tools/convert-grammar-ids.py            # dry run, prints what it would do
  python <voice repo>/Tools/convert-grammar-ids.py --write    # rewrites the grammar in place

Items without a handler are listed on stdout. Check each one: a real command whose handler is missing is a bug to fix
(or a dead phrase to delete) before shipping, not a checklist response. Pass --keep-as-command <name> to keep one in
DISCRETE_COMMANDS; the app's validate-voice.py then reports it until it gets a handler.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--root", default=".", help="aircraft repo root")
parser.add_argument("--grammar", default="CopilotSpeechNew/grammar.xml")
parser.add_argument("--dispatcher", default="CopilotSpeechNew/CommandDispatcher.cs")
parser.add_argument("--ts", default="src/voice/commandDispatch.ts")
parser.add_argument("--keep-as-command", action="append", default=[])
parser.add_argument("--write", action="store_true")
args = parser.parse_args()

root = Path(args.root)
grammar_path = root / args.grammar
cs = (root / args.dispatcher).read_text(encoding="utf-8")
table_src = cs[cs.index("DiscreteNames"):]
table_src = table_src[: table_src.index("};")]
table = {int(a): b for a, b in re.findall(r'\[(\d+)\]\s*=\s*"(\w+)"', table_src)}

ts = (root / args.ts).read_text(encoding="utf-8")
# Apps renamed it to DISCRETE_COMMAND_MAP in 2026-10; older copies still use discreteCommandMap
start = re.search(r"(export )?const (DISCRETE_COMMAND_MAP|discreteCommandMap)", ts).start()
blk = ts[start: ts.index("\n}\n", start)]
handled = set(re.findall(r"^  (\w+):", blk, re.M))
keep = set(args.keep_as_command)

src = open(grammar_path, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in src else "\n"
m = re.search(r'([ \t]*<rule id="DISCRETE_COMMANDS">.*?</rule>)', src, re.S)
old_rule = m.group(1)
lines = old_rule.split(nl)
open_idx = next(i for i, l in enumerate(lines) if "<one-of>" in l)
close_idx = max(i for i, l in enumerate(lines) if "</one-of>" in l)

ITEM = re.compile(r'^(\s*)<item>([^<]+)<tag>out\.pid="(\d+)";?</tag></item>\s*$')
before, commands, responses, pending = [], [], [], []
for line in lines[open_idx + 1: close_idx]:
    if not line.strip() or line.strip().startswith("<!--"):
        pending.append(line)
        continue
    im = ITEM.match(line)
    if not im:
        sys.exit(f"Unexpected line in DISCRETE_COMMANDS, convert it by hand first: {line!r}")
    indent, text, pid = im.groups()
    if int(pid) not in table:
        sys.exit(f"Id {pid} ('{text}') is not in DiscreteNames")
    name = table[int(pid)]
    before.append((text, name))
    new_line = f'{indent}<item>{text}<tag>out.pid="{name}";</tag></item>'
    if name in handled or name in keep:
        commands.extend(pending)
        commands.append(new_line)
    else:
        responses.append(new_line)
    pending = []

new_discrete = nl.join(lines[: open_idx + 1] + commands + lines[close_idx:])
responses_rule = nl.join([
    "  <!-- ═══════════════════════════════════════════════════════════════════════════",
    "       CHECKLIST_RESPONSES  (no handler; checklistRunner.ts matches them by spoken text)",
    "  ════════════════════════════════════════════════════════════════════════════ -->",
    '  <rule id="CHECKLIST_RESPONSES">',
    "    <one-of>",
    *responses,
    "    </one-of>",
    "  </rule>",
])
out = src.replace(old_rule, new_discrete + nl + nl + responses_rule)

top = re.search(r'([ \t]*)<tag>out\.ActionRuleId="DISCRETE_COMMANDS"; out\.CmdId=rules\.DISCRETE_COMMANDS\.pid;</tag>\r?\n([ \t]*)</item>', out)
if not top:
    sys.exit("TOPLEVEL routing for DISCRETE_COMMANDS not found in the expected form; add the CHECKLIST_RESPONSES item by hand")
tag_indent, item_indent = top.group(1), top.group(2)
routing = nl.join([
    top.group(0),
    f"{item_indent}<item>",
    f'{tag_indent}<ruleref uri="#CHECKLIST_RESPONSES" />',
    f'{tag_indent}<tag>out.ActionRuleId="DISCRETE_COMMANDS"; out.CmdId=rules.CHECKLIST_RESPONSES.pid;</tag>',
    f"{item_indent}</item>",
])
out = out.replace(top.group(0), routing, 1)


def rule_items(text, rule_id):
    body = re.search(rf'<rule id="{rule_id}">(.*?)</rule>', text, re.S).group(1)
    return re.findall(r'<item>([^<]+)<tag>out\.pid="([^"]+)";</tag></item>', body)


new_cmds = rule_items(out, "DISCRETE_COMMANDS")
new_resp = rule_items(out, "CHECKLIST_RESPONSES")
assert Counter(before) == Counter(new_cmds + new_resp), "a phrase changed its command name"
for _, pid in new_cmds + new_resp:
    assert re.fullmatch(r"[a-z][a-z0-9_]*", pid), f"not snake_case: {pid}"
def other_rules(t):
    rules = dict(re.findall(r'<rule id="([^"]+)"[^>]*>(.*?)</rule>', t, re.S))
    return {k: v for k, v in rules.items() if k not in ("DISCRETE_COMMANDS", "CHECKLIST_RESPONSES", "TOPLEVEL")}


assert other_rules(src) == other_rules(out), "a rule other than DISCRETE_COMMANDS/TOPLEVEL changed"

print(f"{len(new_cmds)} command items ({len({p for _, p in new_cmds})} ids), "
      f"{len(new_resp)} response items ({len({p for _, p in new_resp})} ids)")
print("Moved to CHECKLIST_RESPONSES (no handler) - check none of these is a real command:")
print("  " + ", ".join(sorted({p for _, p in new_resp})))
if args.write:
    open(grammar_path, "w", encoding="utf-8", newline="").write(out)
    print(f"Written: {grammar_path}")
else:
    print("Dry run; pass --write to rewrite the grammar")
