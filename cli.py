import argparse
import json
import os
import sys

from main import CONFIG_FILE


def load_raw_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    tmp_path = f"{CONFIG_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, CONFIG_FILE)


def cmd_list(_args):
    config = load_raw_config()
    watch_list = config.get("watch_list", [])
    if not watch_list:
        print("감시 중인 상품이 없습니다.")
        return
    print(f"감시 중인 상품 ({len(watch_list)}개):")
    for item in watch_list:
        model = item.get("model", "?")
        target = item.get("target_price", 0)
        print(f"  - {model}: 목표가 {target:,}원")


def cmd_add(args):
    if args.target_price <= 0:
        print("목표가는 양의 정수여야 합니다.", file=sys.stderr)
        raise SystemExit(1)

    config = load_raw_config()
    watch_list = config.setdefault("watch_list", [])

    if any(item.get("model") == args.model for item in watch_list):
        print(f"이미 감시 중인 상품입니다: {args.model}", file=sys.stderr)
        raise SystemExit(1)

    watch_list.append({"model": args.model, "target_price": args.target_price})
    save_config(config)
    print(f"추가됨: {args.model} (목표가 {args.target_price:,}원)")


def cmd_remove(args):
    config = load_raw_config()
    watch_list = config.get("watch_list", [])

    new_list = [item for item in watch_list if item.get("model") != args.model]
    if len(new_list) == len(watch_list):
        print(f"해당 상품을 찾을 수 없습니다: {args.model}", file=sys.stderr)
        raise SystemExit(1)

    config["watch_list"] = new_list
    save_config(config)
    print(f"제거됨: {args.model}")


def main():
    parser = argparse.ArgumentParser(description="가격 감시 상품 관리 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="감시 상품 목록 조회")

    add_parser = subparsers.add_parser("add", help="감시 상품 추가")
    add_parser.add_argument("model", help="다나와 검색 모델명")
    add_parser.add_argument("target_price", type=int, help="목표가 (원)")

    remove_parser = subparsers.add_parser("remove", help="감시 상품 삭제")
    remove_parser.add_argument("model", help="삭제할 모델명")

    args = parser.parse_args()

    commands = {"list": cmd_list, "add": cmd_add, "remove": cmd_remove}
    commands[args.command](args)


if __name__ == "__main__":
    main()
