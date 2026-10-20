"""Write queued D1 rows with the LIVE schema (the 20 Oct run found hand-written rows using wrong columns).
  findings(doc, title, date, verdict, superseded_by, summary)      rules(id, rule, why, doc, added)
Usage: from d1_queue import finding, rule, queue;  queue(date, [finding(...), rule(...)])"""
def q(s): return str(s).replace("'", "''")
def finding(doc, title, date, verdict, summary):
    return f"INSERT OR REPLACE INTO findings (doc, title, date, verdict, superseded_by, summary) VALUES ({int(doc)}, '{q(title)}', '{date}', '{q(verdict)}', NULL, '{q(summary)}');"
def rule(id_, text, why, doc, added):
    return f"INSERT OR REPLACE INTO rules (id, rule, why, doc, added) VALUES ({int(id_)}, '{q(text)}', '{q(why)}', {int(doc)}, '{added}');"
def queue(date, lines, runs="/home/claude/qlab/runs"):
    p = f"{runs}/pending_d1_{date}.sql"; open(p, "a").write("\n".join(lines) + "\n"); return p
