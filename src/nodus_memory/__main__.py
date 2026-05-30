from __future__ import annotations

import argparse
import json
import sys


def _make_store(args):
    from nodus_memory import MemoryStore, MemoryConfig
    return MemoryStore(MemoryConfig(
        tenant_id=getattr(args, "tenant", "default"),
        namespace=getattr(args, "namespace", "default"),
    ))


def cmd_store(args):
    store = _make_store(args)
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    store.put(args.key, value)
    print(json.dumps({"stored": args.key}))


def cmd_recall(args):
    store = _make_store(args)
    value = store.get(args.key)
    if value is None:
        print("null")
    else:
        print(json.dumps(value))


def cmd_list(args):
    store = _make_store(args)
    tag = getattr(args, "tag", None)
    path = getattr(args, "path", None)
    nodes = store.recall_all(tag=tag, path_prefix_override=path)
    for node in nodes:
        print(json.dumps({"key": node.key, "value": node.value, "tags": sorted(node.tags)}))


def cmd_tag(args):
    store = _make_store(args)
    tags = frozenset(args.tags)
    store.tag(args.key, tags)
    print(json.dumps({"tagged": args.key, "tags": sorted(tags)}))


def cmd_feedback(args):
    store = _make_store(args)
    success = args.outcome == "success"
    store.record_feedback(args.key, success=success)
    print(json.dumps({"key": args.key, "feedback": args.outcome}))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="nodus-memory",
        description="nodus-memory CLI — interact with a memory store",
    )
    parser.add_argument("--version", action="version", version="nodus-memory 0.1.0")
    parser.add_argument("--tenant", default="default", help="tenant ID (default: 'default')")
    parser.add_argument("--namespace", default="default", help="namespace (default: 'default')")

    sub = parser.add_subparsers(dest="command", required=True)

    p_store = sub.add_parser("store", help="Store a key/value pair")
    p_store.add_argument("key")
    p_store.add_argument("value", help="JSON value or plain string")
    p_store.set_defaults(func=cmd_store)

    p_recall = sub.add_parser("recall", help="Retrieve a value by key")
    p_recall.add_argument("key")
    p_recall.set_defaults(func=cmd_recall)

    p_list = sub.add_parser("list", help="List stored nodes")
    p_list.add_argument("--tag", help="Filter by tag")
    p_list.add_argument("--path", help="Filter by MAS path prefix")
    p_list.set_defaults(func=cmd_list)

    p_tag = sub.add_parser("tag", help="Tag a key")
    p_tag.add_argument("key")
    p_tag.add_argument("tags", nargs="+", metavar="TAG")
    p_tag.set_defaults(func=cmd_tag)

    p_fb = sub.add_parser("feedback", help="Record outcome feedback for a key")
    p_fb.add_argument("key")
    p_fb.add_argument("outcome", choices=["success", "failure"])
    p_fb.set_defaults(func=cmd_feedback)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
