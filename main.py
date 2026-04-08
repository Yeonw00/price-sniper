import json
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_danawa_lowest_price(model_name, config):
    min_price_filter = config.get("min_price_filter", 100000)
    url = config.get("search_url", "https://search.danawa.com/dsearch.php")
    user_agent = config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    css_selector = config.get("price_css_selector", ".price_sect strong")
    currency = config.get("currency_symbol", "원")

    params = {"query": model_name}
    headers = {"User-Agent": user_agent}

    print(f"[{model_name}] 검색 결과를 가져오는 중...")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 주의: 다나와 웹페이지 구조에 따라 config.json의 price_css_selector 수정이 필요할 수 있습니다.
    price_elements = soup.select(css_selector)

    if price_elements:
        price_list = []

        for element in price_elements:
            raw_text = element.text.strip()
            try:
                price_part = raw_text.split(currency)[0]
                price = int(price_part.replace(",", "").strip())

                if price > min_price_filter:
                    price_list.append(price)
            except ValueError:
                continue

        if price_list:
            lowest_price = min(price_list)
            print(f"수집된 전체 가격들: {price_list}")
            return lowest_price
        else:
            print("조건에 맞는 유효한 가격을 찾지 못했습니다.")
            return None

    else:
        print("해당 선택자로 요소를 찾지 못했습니다.")
        return None


def send_email_alert(subject, body, to_email):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not all([smtp_server, smtp_port, sender_email, sender_password]):
        print(".env 파일에 SMTP/이메일 계정 정보가 누락되어 있습니다!")
        return None

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()  # TLS 보안 연결
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("성공적으로 이메일 알림을 보냈습니다!")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")


def main():
    config = load_config()
    my_email = os.getenv("RECEIVER_EMAIL")

    for item in config["watch_list"]:
        target_model = item["model"]
        target_price = item["target_price"]

        current_price = get_danawa_lowest_price(target_model, config)

        if current_price is not None:
            print(f"[{target_model}] 현재 최저가: {current_price:,}원")

            if current_price <= target_price:
                subject = f"[최저가 알림] {target_model} 가격 하락!"
                body = f"기다리시던 {target_model}의 현재 최저가가 {current_price:,}원으로 떨어졌습니다.\n목표가: {target_price:,}원"
                send_email_alert(subject, body, my_email)
            else:
                print(f"[{target_model}] 아직 목표가({target_price:,}원)까지 떨어지지 않았습니다.")
        else:
            print(f"[{target_model}] 가격을 파싱하지 못했습니다. HTML 구조나 CSS 선택자를 확인해 주세요.")


if __name__ == "__main__":
    main()
