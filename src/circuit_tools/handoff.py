"""Stage handoff records (plan section 4: I-1 model to design, I-2 design to test; plus the simulation assessment).

Frozen 2 October 2026 for the E2E-0 pilot (scripts/e2e_pilot.py), before any run. A record is a JSON object; this
module checks its structure and the rules that tie its status to its checks, exceptions and upstream records. It
does not judge engineering content: whether a claim is warranted is reviewed separately, and whether the cited
artifacts say what the record says is recomputed by the independent checker (scripts/e2e_check.py).

Common fields (every kind):
  schema       "handoff-i1/1", "handoff-i2/1" or "sim-assessment/1"
  produced_by  "reference" (deterministic script) or "agent"
  status       complete     every check passed, no open exception
               provisional  usable downstream with the listed exceptions; every failed check is an exception
               incomplete   some required work did not finish (stop_reason says what)
               failed       a required check failed and the stage cannot hand off a usable result
               rejected_input an upstream record or input was unusable (missing, failed, or hash mismatch);
                            nothing is predicted from it
  stop_reason  null for complete/provisional; a nonempty string otherwise
  inputs       [{path, sha256, role}]  files consumed, upstream records included (paths relative to the workspace)
  artifacts    [{path, sha256, role}]  files produced
  checks       [{id, description, outcome: pass|fail|not_run, evidence: [paths]}]
  exceptions   [{id, description, consequence}]  open items carried downstream (failed checks among them)
  claims       [{statement, scope, status: supported|not_supported|unresolved, evidence: [paths]}]
  assumptions  [{name, value, units, source}]  assumed (not extracted, measured or datasheet) parameters
Kind-specific fields:
  I-1          model {library, sha256, subckt, modified: false}; simulator {name, settings}
  I-2          upstream {path, sha256} (the I-1 record); network {extraction, variant, mesh, junction};
               predictions [{case, metric, value, units, usable}]
  assessment   upstream {path, sha256} (the I-2 record); reference_data {path, sha256, description};
               needed_measurements [{quantity, reason}]
Rules: a downstream record inherits every upstream exception id (or is rejected_input); it is complete only if
its upstream is complete; rejected_input/failed/incomplete records carry no predictions; evidence paths must be
listed among inputs or artifacts.

Revision 2 (5 October 2026, project audit at f4767b1, finding 4): nested fields are type-checked before they are
hashed or compared, so a malformed record (evidence entries that are not strings, ids that are not strings)
yields structured problems instead of an exception. The rules themselves are unchanged.
"""
from __future__ import annotations

import re
from typing import Any

KINDS = {"handoff-i1/1": "I-1", "handoff-i2/1": "I-2", "sim-assessment/1": "assessment"}
STATUSES = ("complete", "provisional", "incomplete", "failed", "rejected_input")
STOPPED = ("incomplete", "failed", "rejected_input")
OUTCOMES = ("pass", "fail", "not_run")
CLAIM_STATUS = ("supported", "not_supported", "unresolved")
SHA = re.compile(r"^[0-9a-f]{64}$")


def _str(x) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _paths_among(v, paths) -> bool:
    return isinstance(v, list) and all(isinstance(e, str) and e in paths for e in v)


def _files(rec, key, problems):
    v = rec.get(key)
    if not isinstance(v, list):
        problems.append(f"{key} is not a list")
        return []
    out = []
    for i, f in enumerate(v):
        if not (isinstance(f, dict) and _str(f.get("path")) and isinstance(f.get("sha256"), str)
                and SHA.match(f["sha256"]) and _str(f.get("role"))):
            problems.append(f"{key}[{i}] needs path, 64-hex sha256 and role")
        else:
            out.append(f["path"])
    return out


def _list_of(rec, key, fields, problems):
    v = rec.get(key)
    if not isinstance(v, list):
        problems.append(f"{key} is not a list")
        return []
    for i, x in enumerate(v):
        if not isinstance(x, dict) or any(f not in x for f in fields):
            problems.append(f"{key}[{i}] needs {', '.join(fields)}")
    return [x for x in v if isinstance(x, dict)]


def validate(rec: Any, upstream: Any = None) -> list[str]:
    """Problems with a record (empty if valid). upstream: the parsed upstream record, when there is one."""
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]
    p: list[str] = []
    schema = rec.get("schema")
    kind = KINDS.get(schema) if isinstance(schema, str) else None
    if kind is None:
        return [f"unknown schema {rec.get('schema')!r}"]
    if rec.get("produced_by") not in ("reference", "agent"):
        p.append("produced_by must be reference or agent")
    status = rec.get("status")
    if status not in STATUSES:
        p.append(f"status {status!r} not in {STATUSES}")
    stopped = status in STOPPED
    if stopped and not _str(rec.get("stop_reason")):
        p.append(f"status {status} needs a stop_reason")
    if not stopped and rec.get("stop_reason") is not None:
        p.append("stop_reason must be null unless the record is stopped")
    paths = set(_files(rec, "inputs", p)) | set(_files(rec, "artifacts", p))
    checks = _list_of(rec, "checks", ("id", "description", "outcome", "evidence"), p)
    for i, c in enumerate(checks):
        if not _str(c.get("id")):
            p.append(f"checks[{i}]: id must be a nonempty string")
        if c.get("outcome") not in OUTCOMES:
            p.append(f"check {c.get('id')!r}: outcome {c.get('outcome')!r} not in {OUTCOMES}")
        if not _paths_among(c.get("evidence"), paths):
            p.append(f"check {c.get('id')!r}: evidence must list paths among inputs/artifacts")
    ids = [c.get("id") for c in checks]
    if len(set(map(str, ids))) != len(ids):
        p.append("duplicate check ids")
    exceptions = _list_of(rec, "exceptions", ("id", "description", "consequence"), p)
    for i, e in enumerate(exceptions):
        if not _str(e.get("id")):
            p.append(f"exceptions[{i}]: id must be a nonempty string")
    exc_ids = {e.get("id") for e in exceptions if _str(e.get("id"))}
    claims = _list_of(rec, "claims", ("statement", "scope", "status", "evidence"), p)
    for i, c in enumerate(claims):
        if not (_str(c.get("statement")) and _str(c.get("scope"))):
            p.append(f"claims[{i}] needs a nonempty statement and scope")
        if c.get("status") not in CLAIM_STATUS:
            p.append(f"claims[{i}]: status {c.get('status')!r} not in {CLAIM_STATUS}")
        ev = c.get("evidence")
        if not ev or not _paths_among(ev, paths):
            p.append(f"claims[{i}]: evidence must be a nonempty list of paths among inputs/artifacts")
    for i, a in enumerate(_list_of(rec, "assumptions", ("name", "value", "units", "source"), p)):
        if not (_str(a.get("name")) and isinstance(a.get("units"), str) and _str(a.get("source"))
                and isinstance(a.get("value"), (int, float, str, bool))):
            p.append(f"assumptions[{i}] needs name, scalar value, units string and source")
    failed = {c.get("id") for c in checks if c.get("outcome") == "fail" and _str(c.get("id"))}
    not_run = {c.get("id") for c in checks if c.get("outcome") == "not_run" and _str(c.get("id"))}
    if status == "complete" and (failed or not_run or exceptions):
        p.append("complete requires every check passed and no exceptions")
    if status == "provisional" and not failed <= exc_ids:
        p.append(f"provisional: failed checks {sorted(map(str, failed - exc_ids))} are not listed as exceptions")
    if status == "provisional" and not_run and not not_run <= exc_ids:
        p.append("provisional: checks not run must be listed as exceptions")
    # kind-specific
    if kind == "I-1":
        m = rec.get("model")
        if not (isinstance(m, dict) and _str(m.get("library")) and isinstance(m.get("sha256"), str)
                and SHA.match(m["sha256"]) and _str(m.get("subckt")) and m.get("modified") is False):
            p.append("I-1 model needs library, sha256, subckt and modified: false")
        s = rec.get("simulator")
        if not (isinstance(s, dict) and _str(s.get("name")) and isinstance(s.get("settings"), dict)):
            p.append("I-1 simulator needs name and settings")
    else:
        up = rec.get("upstream")
        if not (isinstance(up, dict) and _str(up.get("path")) and isinstance(up.get("sha256"), str)
                and SHA.match(up["sha256"])):
            p.append("upstream needs path and sha256")
        elif up["path"] not in paths:
            p.append("the upstream record must be listed among inputs")
        if upstream is not None and isinstance(upstream, dict):
            u_status = upstream.get("status")
            if u_status in STOPPED and status != "rejected_input":
                p.append(f"upstream is {u_status}: this record must be rejected_input")
            if status == "complete" and u_status != "complete":
                p.append("complete requires a complete upstream")
            if status in ("complete", "provisional"):
                up_exc = upstream.get("exceptions")
                up_exc = up_exc if isinstance(up_exc, list) else []
                missing = {str(e.get("id")) for e in up_exc if isinstance(e, dict)} - exc_ids
                if missing:
                    p.append(f"upstream exceptions not carried: {sorted(map(str, missing))}")
    if kind == "I-2":
        n = rec.get("network")
        if not (isinstance(n, dict) and all(_str(n.get(k)) for k in ("extraction", "variant", "mesh", "junction"))):
            p.append("I-2 network needs extraction, variant, mesh and junction")
        preds = _list_of(rec, "predictions", ("case", "metric", "value", "units", "usable"), p)
        if stopped and preds:
            p.append(f"a {status} record carries no predictions")
        for i, x in enumerate(preds):
            if not (isinstance(x.get("value"), (int, float)) or x.get("value") is None) or \
                    not isinstance(x.get("usable"), bool) or not isinstance(x.get("units"), str):
                p.append(f"predictions[{i}] needs a numeric (or null) value, units string and boolean usable")
    if kind == "assessment":
        r = rec.get("reference_data")
        if not stopped and not (isinstance(r, dict) and _str(r.get("path")) and _str(r.get("description"))
                                and isinstance(r.get("sha256"), str) and SHA.match(r["sha256"])):
            p.append("assessment reference_data needs path, sha256 and description")
        _list_of(rec, "needed_measurements", ("quantity", "reason"), p)
    return p
