import json
import logging
import time
import os
from datetime import datetime
from main import get_danawa_lowest_price, send_email_alert, load_config, setup_logging
from dotenv import load_dotenv

load_dotenv()

config = load_config()
setup_logging(config)
logger = logging.getLogger(__name__)
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_history.json")
CHECK_INTERVAL_MINUTES = config.get("check_interval_minutes", 30)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def check_and_alert(model_name):
    history = load_history()
    record = history.get(model_name, {"lowest_price": None})

    current_price = get_danawa_lowest_price(model_name, config)
    if current_price is None:
        logger.warning(f"[{model_name}] 가격을 가져오지 못했습니다.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev_lowest = record.get("lowest_price")

    if prev_lowest:
        logger.info(f"[{model_name}] 현재가: {current_price:,}원 | 역대 최저가: {prev_lowest:,}원")
    else:
        logger.info(f"[{model_name}] 현재가: {current_price:,}원 | 첫 조회")

    if prev_lowest is None or current_price < prev_lowest:
        # 역대 최저가 갱신
        record["lowest_price"] = current_price
        record["updated_at"] = now
        history[model_name] = record
        save_history(history)

        receiver = os.getenv("RECEIVER_EMAIL")
        if prev_lowest is None:
            subject = f"[최저가 등록] {model_name} - {current_price:,}원"
            body = (
                f"모델: {model_name}\n"
                f"현재 최저가: {current_price:,}원\n"
                f"조회 시간: {now}\n\n"
                f"첫 조회이므로 기준가로 등록합니다."
            )
        else:
            diff = prev_lowest - current_price
            subject = f"[최저가 갱신] {model_name} - {current_price:,}원 ({diff:,}원 하락)"
            body = (
                f"모델: {model_name}\n"
                f"이전 최저가: {prev_lowest:,}원\n"
                f"현재 최저가: {current_price:,}원\n"
                f"하락폭: {diff:,}원\n"
                f"조회 시간: {now}"
            )

        logger.info(f"[{model_name}] 최저가 갱신! 알림 발송 중...")
        send_email_alert(subject, body, receiver)
    else:
        logger.info(f"[{model_name}] 최저가 변동 없음.")


def main():
    watch_list = [item["model"] for item in config["watch_list"]]

    logger.info(f"=== 가격 감시 배치 시작 (주기: {CHECK_INTERVAL_MINUTES}분) ===")
    logger.info(f"감시 대상: {watch_list}")

    while True:
        for model in watch_list:
            try:
                check_and_alert(model)
            except Exception as e:
                logger.error(f"[{model}] 오류 발생: {e}")

        logger.info(f"다음 조회까지 {CHECK_INTERVAL_MINUTES}분 대기...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
